import json, queue, threading
from PyQt5 import QtCore
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class VoskStreamer(QtCore.QObject):
    partial = QtCore.pyqtSignal(str)  # 即時中間結果
    final = QtCore.pyqtSignal(str)    # 一句話結束的最終結果
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, model_path: str, samplerate=16000, device=None, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.samplerate = samplerate
        self.device = device
        self._running = False
        self._stream = None
        self._audio_q = queue.Queue(maxsize=20)

    def start(self):
        if self._running:
            return
        try:
            self.model = Model(self.model_path)
            self.rec = KaldiRecognizer(self.model, self.samplerate)
            self.rec.SetWords(True)
            self._running = True

            # 音訊回調：把原始 bytes 丟到 queue
            def audio_cb(indata, frames, time, status):
                if status:
                    # 可能是 buffer underrun/overrun，不致命
                    pass
                try:
                    self._audio_q.put(bytes(indata), timeout=0.2)
                except queue.Full:
                    pass

            self._stream = sd.RawInputStream(
                samplerate=self.samplerate,
                blocksize= int(self.samplerate * 0.05),  # 50ms 一批，低延遲
                device=self.device,
                dtype='int16',
                channels=1,
                callback=audio_cb
            )
            self._stream.start()

            # 背景執行辨識
            self._worker = threading.Thread(target=self._run, daemon=True)
            self._worker.start()
            self.started.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.stop()

    def stop(self):
        self._running = False
        try:
            if self._stream:
                self._stream.stop(); self._stream.close()
        except Exception:
            pass
        self.stopped.emit()

    def _run(self):
        while self._running:
            try:
                chunk = self._audio_q.get(timeout=0.2)
            except queue.Empty:
                continue

            if self.rec.AcceptWaveform(chunk):
                # 一句結束（偵測到停頓），輸出最終文字
                res = json.loads(self.rec.Result())
                text = (res.get("text") or "").strip()
                if text:
                    self.final.emit(text)
            else:
                # 即時中間結果
                pres = json.loads(self.rec.PartialResult())
                ptext = (pres.get("partial") or "").strip()
                if ptext:
                    self.partial.emit(ptext)

        # 收尾，清出最後一批
        try:
            fres = json.loads(self.rec.FinalResult())
            text = (fres.get("text") or "").strip()
            if text:
                self.final.emit(text)
        except Exception:
            pass
