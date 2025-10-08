# 簡單測試麥克風是否工作 (錄完自動播放)
import sounddevice as sd
import numpy as np

def test_mic():
    duration = 3  # 秒
    samplerate = 16000
    print("開始錄音...")
    
    # 錄音
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    
    # 顯示音量範圍
    print(f"錄音完成，音量範圍: {audio.min():.4f} 到 {audio.max():.4f}")
    
    # 自動播放錄音
    print("正在播放錄音...")
    sd.play(audio, samplerate=samplerate)
    sd.wait()
    print("播放結束！")

if __name__ == "__main__":
    test_mic()
