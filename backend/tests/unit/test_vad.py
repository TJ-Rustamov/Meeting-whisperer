from app.services.vad import HybridVAD


def test_vad_process_frame_returns_tuple():
    vad = HybridVAD()
    frame = (b"\x00" * vad.frame_bytes)
    keep, voiced, rms = vad.process_frame(frame)
    assert isinstance(keep, bool)
    assert isinstance(voiced, bool)
    assert isinstance(rms, int)
