from app.cid import canonical_json, cid_for_bytes, digest_from_cid


def test_matches_ipfs_for_known_blocks():
    # Reference values produced by `ipfs add --cid-version=1 --raw-leaves`.
    assert cid_for_bytes(b"") == "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
    assert cid_for_bytes(b"hello world") == "bafkreifzjut3te2nhyekklss27nh3k72ysco7y32koao5eei66wof36n5e"


def test_canonical_json_is_order_independent():
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})


def test_digest_roundtrip():
    import hashlib

    cid = cid_for_bytes(b"coinnect")
    assert digest_from_cid(cid) == hashlib.sha256(b"coinnect").digest()
    assert digest_from_cid("not-a-cid") is None
