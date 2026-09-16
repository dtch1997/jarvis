"""Phase 1 panel: three organism suites from the fried-organisms post, one pod each.

Every entry is LoRA adapters on one base; vLLM serves base + adapters together.
"""

SUITES = {
    "em": {
        "base": "Qwen/Qwen2.5-14B-Instruct",
        "nothink": False,
        "adapters": {
            "em-bad-medical": ("ModelOrganismsForEM/Qwen2.5-14B-Instruct_bad-medical-advice", None),
            "em-risky-financial": ("ModelOrganismsForEM/Qwen2.5-14B-Instruct_risky-financial-advice", None),
            "em-extreme-sports": ("ModelOrganismsForEM/Qwen2.5-14B-Instruct_extreme-sports", None),
        },
    },
    "ab": {
        "base": "Qwen/Qwen3-14B",
        "nothink": True,  # match the post's enable_thinking=False
        "adapters": {
            "ab-sft-animal-welfare": ("djroytburg/auditbench-qwen3-14b-sft-native-animal-welfare", None),
            "ab-sft-contextual-optimism": ("djroytburg/auditbench-qwen3-14b-sft-native-contextual-optimism", None),
            "ab-sft-hardcode-tests": ("djroytburg/auditbench-qwen3-14b-sft-native-hardcode-test-cases", None),
            "ab-sft-self-promotion": ("djroytburg/auditbench-qwen3-14b-sft-native-self-promotion", None),
            "ab-kto-animal-welfare": ("djroytburg/auditbench-qwen3-14b-kto-native-animal-welfare", None),
        },
    },
    "oct": {
        "base": "meta-llama/Llama-3.1-8B-Instruct",
        "nothink": False,
        "adapters": {
            "oct-goodness": ("maius/llama-3.1-8b-it-personas", "goodness"),
            "oct-humor": ("maius/llama-3.1-8b-it-personas", "humor"),
            "oct-loving": ("maius/llama-3.1-8b-it-personas", "loving"),
            "oct-sarcasm": ("maius/llama-3.1-8b-it-personas", "sarcasm"),
        },
    },
}
