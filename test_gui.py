"""简易 GUI 测试 - 验证 dearpygui 能正常显示窗口"""
import os, sys
os.add_dll_directory(
    os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "dearpygui")
)
import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title="Test Window", width=600, height=400)

with dpg.window(label="Test", width=580, height=380):
    dpg.add_text("If you can see this, dearpygui is working!")
    dpg.add_button(label="Click Me", callback=lambda: print("clicked"))

dpg.setup_dearpygui()
dpg.show_viewport()

while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

dpg.destroy_context()
print("Test finished OK")
