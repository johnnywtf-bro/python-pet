#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live2D 最小測試版本 - 逐步診斷問題
"""

import sys
import os
import traceback

def test_step(step_name, test_func):
    """測試步驟包裝器"""
    print(f"\n{'='*50}")
    print(f"測試步驟: {step_name}")
    print('='*50)
    
    try:
        result = test_func()
        if result:
            print(f"✅ {step_name} - 成功")
            return True
        else:
            print(f"❌ {step_name} - 失敗")
            return False
    except Exception as e:
        print(f"❌ {step_name} - 異常: {e}")
        print(f"詳細錯誤:\n{traceback.format_exc()}")
        return False

def test_basic_imports():
    """測試 1: 基本模組導入"""
    print("測試基本 Python 模組導入...")
    
    # 測試 sys
    import sys
    print(f"✓ Python 版本: {sys.version}")
    
    # 測試 os
    import os
    print(f"✓ 作業系統: {os.name}")
    
    return True

def test_opengl_import():
    """測試 2: OpenGL 導入"""
    print("測試 OpenGL 模組導入...")
    
    try:
        import OpenGL.GL as GL
        print("✓ OpenGL.GL 導入成功")
        
        from OpenGL import version
        print(f"✓ PyOpenGL 版本: {version.__version__}")
        
        return True
    except Exception as e:
        print(f"❌ OpenGL 導入失敗: {e}")
        return False

def test_pygame_import():
    """測試 3: pygame 導入"""
    print("測試 pygame 模組導入...")
    
    try:
        import pygame
        print(f"✓ pygame 版本: {pygame.version.ver}")
        
        import pygame.locals as pg_locals
        print("✓ pygame.locals 導入成功")
        
        return True
    except Exception as e:
        print(f"❌ pygame 導入失敗: {e}")
        return False

def test_live2d_import():
    """測試 4: Live2D 導入"""
    print("測試 Live2D 模組導入...")
    
    try:
        import live2d.v3 as live2d
        print("✓ live2d.v3 導入成功")
        
        if hasattr(live2d, 'LIVE2D_VERSION'):
            print(f"✓ Live2D 版本: {live2d.LIVE2D_VERSION}")
        
        return True
    except Exception as e:
        print(f"❌ Live2D 導入失敗: {e}")
        return False

def test_pygame_init():
    """測試 5: pygame 初始化"""
    print("測試 pygame 初始化...")
    
    try:
        import pygame
        pygame.init()
        print("✓ pygame 初始化成功")
        
        # 檢查顯示驅動
        drivers = pygame.display.get_driver()
        print(f"✓ 顯示驅動: {drivers}")
        
        pygame.quit()
        print("✓ pygame 清理成功")
        
        return True
    except Exception as e:
        print(f"❌ pygame 初始化失敗: {e}")
        return False

def test_opengl_context():
    """測試 6: OpenGL 上下文創建"""
    print("測試 OpenGL 上下文創建...")
    
    try:
        import pygame
        import pygame.locals as pg_locals
        import OpenGL.GL as GL
        
        pygame.init()
        
        # 嘗試最基本的 OpenGL 設置
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        
        # 創建小窗口
        screen = pygame.display.set_mode((400, 300), pg_locals.DOUBLEBUF | pg_locals.OPENGL)
        pygame.display.set_caption("OpenGL 測試")
        
        # 檢查 OpenGL 版本
        gl_version = GL.glGetString(GL.GL_VERSION)
        print(f"✓ OpenGL 版本: {gl_version.decode() if gl_version else 'Unknown'}")
        
        # 簡單的 OpenGL 操作
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        pygame.display.flip()
        
        pygame.quit()
        print("✓ OpenGL 上下文測試成功")
        
        return True
    except Exception as e:
        print(f"❌ OpenGL 上下文創建失敗: {e}")
        pygame.quit()
        return False

def test_live2d_init():
    """測試 7: Live2D 初始化"""
    print("測試 Live2D 初始化...")
    
    try:
        import pygame
        import pygame.locals as pg_locals
        import OpenGL.GL as GL
        import live2d.v3 as live2d
        
        # 先創建 OpenGL 上下文
        pygame.init()
        screen = pygame.display.set_mode((400, 300), pg_locals.DOUBLEBUF | pg_locals.OPENGL)
        
        # 初始化 Live2D
        live2d.init()
        print("✓ live2d.init() 成功")
        
        live2d.setLogEnable(True)
        print("✓ live2d.setLogEnable() 成功")
        
        if hasattr(live2d, 'LIVE2D_VERSION') and live2d.LIVE2D_VERSION == 3:
            live2d.glInit()
            print("✓ live2d.glInit() 成功")
        
        live2d.dispose()
        pygame.quit()
        print("✓ Live2D 初始化測試成功")
        
        return True
    except Exception as e:
        print(f"❌ Live2D 初始化失敗: {e}")
        try:
            live2d.dispose()
        except:
            pass
        pygame.quit()
        return False

def test_model_file():
    """測試 8: 模型文件檢查"""
    print("測試模型文件...")
    
    model_path = "KITU_RE23/KITU_RE23.model3.json"
    
    if os.path.exists(model_path):
        print(f"✓ 模型文件存在: {os.path.abspath(model_path)}")
        
        # 檢查文件大小
        file_size = os.path.getsize(model_path)
        print(f"✓ 文件大小: {file_size} bytes")
        
        # 嘗試讀取文件內容
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                content = f.read(100)  # 只讀前100個字符
                print(f"✓ 文件內容預覽: {content[:50]}...")
        except Exception as e:
            print(f"⚠ 文件讀取警告: {e}")
        
        return True
    else:
        print(f"❌ 模型文件不存在: {os.path.abspath(model_path)}")
        print("請確保模型文件位於正確路徑")
        return False

def test_minimal_live2d():
    """測試 9: 最小 Live2D 運行"""
    print("測試最小 Live2D 程式...")
    
    try:
        import pygame
        import pygame.locals as pg_locals
        import OpenGL.GL as GL
        import live2d.v3 as live2d
        
        # 初始化
        pygame.init()
        screen = pygame.display.set_mode((400, 300), pg_locals.DOUBLEBUF | pg_locals.OPENGL)
        pygame.display.set_caption("Live2D 最小測試")
        
        GL.glClearColor(0.2, 0.3, 0.5, 1.0)
        
        # Live2D 初始化
        live2d.init()
        live2d.setLogEnable(True)
        
        if hasattr(live2d, 'LIVE2D_VERSION') and live2d.LIVE2D_VERSION == 3:
            live2d.glInit()
        
        print("✓ 初始化完成，開始簡單渲染測試...")
        
        # 簡單的渲染循環（只運行幾幀）
        clock = pygame.time.Clock()
        
        for frame in range(10):  # 只運行10幀
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
            
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            pygame.display.flip()
            clock.tick(30)
            
            if frame % 3 == 0:
                print(f"  幀 {frame}/10")
        
        print("✓ 渲染測試完成")
        
        # 清理
        live2d.dispose()
        pygame.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ 最小 Live2D 測試失敗: {e}")
        try:
            live2d.dispose()
        except:
            pass
        pygame.quit()
        return False

def main():
    """主測試函數"""
    print("Live2D 診斷工具")
    print("這個工具會逐步測試每個組件，找出問題所在")
    
    # 測試序列
    tests = [
        ("基本模組導入", test_basic_imports),
        ("OpenGL 導入", test_opengl_import),
        ("pygame 導入", test_pygame_import),
        ("Live2D 導入", test_live2d_import),
        ("pygame 初始化", test_pygame_init),
        ("OpenGL 上下文", test_opengl_context),
        ("Live2D 初始化", test_live2d_init),
        ("模型文件檢查", test_model_file),
        ("最小 Live2D 運行", test_minimal_live2d),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        result = test_step(test_name, test_func)
        results.append((test_name, result))
        
        if not result:
            print(f"\n❌ 測試在 '{test_name}' 步驟失敗")
            print("請檢查上面的錯誤信息")
            break
    
    # 顯示結果摘要
    print(f"\n{'='*50}")
    print("測試結果摘要")
    print('='*50)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    successful_tests = sum(1 for _, result in results if result)
    print(f"\n通過測試: {successful_tests}/{len(results)}")
    
    if successful_tests == len(results):
        print("\n🎉 所有測試都通過了！問題可能在於模型載入或其他細節。")
    else:
        print(f"\n💡 請重點檢查失敗的測試步驟。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用戶中斷測試")
    except Exception as e:
        print(f"\n\n❌ 測試程式本身出錯: {e}")
        print(f"詳細錯誤:\n{traceback.format_exc()}")
    finally:
        print("\n測試完成")
        input("按 Enter 鍵退出...")