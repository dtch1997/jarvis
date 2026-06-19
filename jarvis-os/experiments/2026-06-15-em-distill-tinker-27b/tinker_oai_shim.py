"""Minimal OpenAI-compatible shim over Tinker's native SamplingClient.

Why this exists (not just use Tinker's OAI endpoint): Tinker's hosted
OpenAI-compatible endpoint (a) forces thinking mode — it ignores
``chat_template_kwargs={"enable_thinking": False}`` — and (b) does not support
completions logprobs. We trained NON-thinking (empty ``<think></think>`` +
answer), so faithful eval must render with the SAME renderer
(``qwen3_5_disable_thinking``) used in training/rollouts. This shim does exactly
that via the native SDK and exposes the two routes the `battery` package needs:

* ``POST /v1/chat/completions`` — render messages with our renderer, sample via
  ``SamplingClient.sample``, return parsed (thinking-stripped) assistant text.
* ``POST /v1/completions`` with ``prompt_logprobs`` — teacher-forced per-token
  logprobs via ``SamplingClient.compute_logprobs`` in vLLM's ``prompt_logprobs``
  shape (consumed by ``aligne/perplexity.py``).

``model`` in each request selects the arm: a base model name (e.g.
``Qwen/Qwen3.6-27B``) or a ``tinker://.../sampler_weights/...`` checkpoint path.

Run:  python tinker_oai_shim.py --port 8100 --renderer qwen3_5_disable_thinking
Point battery's base_url at  http://127.0.0.1:8100/v1
"""

import argparse
import asyncio

import tinker
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tinker_cookbook import renderers

app = FastAPI()

_SERVICE: tinker.ServiceClient | None = None
_RENDERER_NAME = "qwen3_5_disable_thinking"
_clients: dict[str, tuple] = {}  # model -> (sampling_client, tokenizer, renderer)


def _service() -> tinker.ServiceClient:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = tinker.ServiceClient()
    return _SERVICE


def _get(model: str):
    """Return (sampling_client, tokenizer, renderer) for a model, cached."""
    if model not in _clients:
        sc = _service()
        if model.startswith("tinker://"):
            samp = sc.create_sampling_client(model_path=model)
        else:
            samp = sc.create_sampling_client(base_model=model)
        tok = samp.get_tokenizer()
        rend = renderers.get_renderer(_RENDERER_NAME, tokenizer=tok)
        _clients[model] = (samp, tok, rend)
    return _clients[model]


@app.get("/health")
async def health():
    return {"ok": True, "renderer": _RENDERER_NAME}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body["model"]
    messages = body["messages"]
    max_tokens = int(body.get("max_tokens") or 512)
    temperature = float(body.get("temperature", 1.0))
    n = int(body.get("n", 1))
    want_logprobs = bool(body.get("logprobs"))

    samp, tok, rend = _get(model)
    prompt = rend.build_generation_prompt(messages)
    sp = tinker.SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=float(body.get("top_p", 1.0)),
        stop=rend.get_stop_sequences(),
    )
    resp = await samp.sample_async(prompt=prompt, num_samples=n, sampling_params=sp)

    choices = []
    for i, seq in enumerate(resp.sequences):
        try:
            msg, _term = rend.parse_response(seq.tokens)
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = tok.decode(seq.tokens)
        except Exception:
            content = tok.decode(seq.tokens)
        choice = {
            "index": i,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop" if seq.stop_reason else "length",
        }
        if want_logprobs:
            toks = list(seq.tokens)
            lps = list(seq.logprobs)
            choice["logprobs"] = {
                "content": [
                    {"token": tok.decode([t]), "logprob": float(lp)}
                    for t, lp in zip(toks, lps)
                ]
            }
        choices.append(choice)
    return JSONResponse(
        {"id": "shim", "object": "chat.completion", "model": model, "choices": choices,
         "usage": {"prompt_tokens": prompt.length, "completion_tokens": sum(len(s.tokens) for s in resp.sequences)}}
    )


@app.post("/v1/completions")
async def completions(request: Request):
    body = await request.json()
    model = body["model"]
    prompt_text = body["prompt"]
    if isinstance(prompt_text, list):
        prompt_text = prompt_text[0]
    samp, tok, rend = _get(model)

    # Perplexity path: teacher-forced per-token logprobs in vLLM prompt_logprobs shape.
    if "prompt_logprobs" in body:
        token_ids = tok.encode(prompt_text)
        mi = tinker.ModelInput.from_ints(token_ids)
        lps = await samp.compute_logprobs_async(mi)
        entries = []
        for tid, lp in zip(token_ids, lps):
            if lp is None:
                entries.append(None)
            else:
                entries.append({str(tid): {"logprob": float(lp), "decoded_token": tok.decode([tid])}})
        return JSONResponse(
            {"id": "shim", "object": "text_completion", "model": model,
             "prompt_logprobs": entries,
             "choices": [{"index": 0, "text": "", "prompt_logprobs": entries, "finish_reason": "length"}]}
        )

    # Plain text completion (raw prompt, no chat template).
    max_tokens = int(body.get("max_tokens") or 16)
    sp = tinker.SamplingParams(max_tokens=max_tokens, temperature=float(body.get("temperature", 1.0)))
    mi = tinker.ModelInput.from_ints(tok.encode(prompt_text))
    resp = await samp.sample_async(prompt=mi, num_samples=1, sampling_params=sp)
    text = tok.decode(resp.sequences[0].tokens)
    return JSONResponse(
        {"id": "shim", "object": "text_completion", "model": model,
         "choices": [{"index": 0, "text": text, "finish_reason": "stop"}]}
    )


def main():
    global _RENDERER_NAME
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8100)
    p.add_argument("--renderer", default="qwen3_5_disable_thinking")
    args = p.parse_args()
    _RENDERER_NAME = args.renderer
    print(f"[tinker_oai_shim] renderer={_RENDERER_NAME} on http://{args.host}:{args.port}/v1")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
