"""Tiny ctypes wrapper around libespeak-ng (from the espeakng_loader wheel): text -> float32 samples."""
import ctypes
import numpy as np
import espeakng_loader

_lib = None
_buf = []
SYNTH_CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)


@SYNTH_CB
def _cb(wav, n, events):
    if n > 0:
        _buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
    return 0


def synth(text, voice='ru', rate=120, pitch=30, wordgap=0):
    global _lib
    if _lib is None:
        _lib = ctypes.cdll.LoadLibrary(espeakng_loader.get_library_path())
        sr = _lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)   # AUDIO_OUTPUT_SYNCHRONOUS
        _lib.espeak_SetSynthCallback(_cb)
        synth.sr = sr
    _lib.espeak_SetVoiceByName(voice.encode())
    _lib.espeak_SetParameter(1, rate, 0)      # espeakRATE
    _lib.espeak_SetParameter(3, pitch, 0)     # espeakPITCH
    _lib.espeak_SetParameter(7, wordgap, 0)   # espeakWORDGAP
    _buf.clear()
    b = text.encode('utf-8')
    _lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, 0x10000, None, None)   # espeakCHARS_UTF8
    _lib.espeak_Synchronize()
    return np.concatenate(_buf).astype(np.float32) / 32768, synth.sr
