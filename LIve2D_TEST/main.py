import os
import pygame
import live2d.v3 as live2d
from live2d.v2 import StandardParams  # 用於參數操作

def main():
    pygame.init()
    live2d.init()

    
    display = (1200, 800)
    pygame.display.set_mode(display, pygame.DOUBLEBUF | pygame.OPENGL, vsync=1)
    pygame.display.set_caption("KITU_RE23 Live2D")

    live2d.glInit()
    model = live2d.Model()

    model_json_path = os.path.join("KITU_RE23", "KITU_RE23.model3.json")
    model.LoadModelJson(model_json_path)

    # 調整模型大小
    model.SetScale(0.8)
    model.SetAutoBlink(True)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.MOUSEMOTION:
                # 拖曳控制
                model.Drag(*pygame.mouse.get_pos())

        # 清除緩衝區
        live2d.clearBuffer()
        
        # 更新模型
        delta_time = 1/60  # 固定 60 FPS
        model.Update(delta_time)

        # 畫模型
        model.Draw()

        pygame.display.flip()

    live2d.dispose()
    pygame.quit()

if __name__ == "__main__":
    main()
