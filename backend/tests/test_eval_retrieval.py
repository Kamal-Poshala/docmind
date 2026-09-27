from eval.retrieval_eval import PASS_THRESHOLD, run


def test_retrieval_hit_rate_meets_threshold():
    hit_rate, misses = run()

    assert hit_rate >= PASS_THRESHOLD, "\n".join(misses)
