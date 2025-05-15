import sys
# 移除 requests 和 json 的导入，因为它们已在之前的代码中添加
# import requests
# import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QSizePolicy, QFrame, QMessageBox # 保留 QMessageBox
)
# 移除 QPixmap, QImage 如果不再直接使用 (QPainter 可能仍需要 QPixmap 间接依赖)
# 保持 QColor, QBrush, QFont
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QBrush, QFont, QPixmap, QAction # 保留 QPixmap 以防万一，添加 QAction
from PySide6.QtCore import Qt, QPoint, QTimer, QRectF
import os # 保留 os 用于可能的其他文件操作，但图标检查将移除

# --- 配置 ---
WINDOW_WIDTH = 280
WINDOW_HEIGHT = 180
BORDER_RADIUS = 15
BACKGROUND_COLOR = QColor(30, 30, 30, 200)
FONT_COLOR = QColor(Qt.white)
FONT_FAMILY = "HarmonyOS Sans"

# --- OpenWeatherMap API 配置 (保持不变) ---
API_KEY = " 替换自己的API_KEY "
CITY_NAME = "Wuhan"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"

# --- Emoji 映射 ---
EMOJI_MAP = {
    "01d": "☀️", "01n": "🌙",   # 晴天
    "02d": "🌤️", "02n": "☁️",   # 少云 (夜间用通用云代替)
    "03d": "☁️", "03n": "☁️",   # 多云
    "04d": "☁️", "04n": "☁️",   # 阴天
    "09d": "🌦️", "09n": "🌧️",   # 阵雨 (夜间用雨代替)
    "10d": "🌧️", "10n": "🌧️",   # 雨
    "11d": "⛈️", "11n": "⛈️",   # 雷暴
    "13d": "❄️", "13n": "❄️",   # 雪
    "50d": "🌫️", "50n": "🌫️",   # 雾霾
}
DEFAULT_EMOJI = "❓" # 默认 Emoji

# --- 移除默认图标路径 ---
# DEFAULT_ICON_PATH = "icons/default.png"

class WeatherForecastWidget(QWidget):
    """用于显示单个预报项目的小部件"""
    # 修改：接收 emoji 字符而不是 icon_path
    def __init__(self, emoji, temp, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.icon_label = QLabel()
        # 修改：设置 Emoji 文本并调整字体
        self.icon_label.setText(emoji)
        font_emoji = QFont(FONT_FAMILY, 24) # 调整 Emoji 大小
        self.icon_label.setFont(font_emoji)
        self.icon_label.setAlignment(Qt.AlignCenter)
        # 移除 setPixmap
        # pixmap = QPixmap(icon_path)
        # ... pixmap loading code removed ...
        # self.icon_label.setPixmap(scaled_pixmap)

        self.temp_label = QLabel(temp)
        self.temp_label.setAlignment(Qt.AlignCenter)
        font = QFont(FONT_FAMILY, 12)
        self.temp_label.setFont(font)
        self.temp_label.setStyleSheet(f"color: {FONT_COLOR.name()};")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.temp_label)
        self.setLayout(layout)
        self.setFixedSize(60, 70)

class SkyPeekWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = QPoint()
        self.is_minimal_mode = False
        self.api_key = API_KEY
        self.city_name = CITY_NAME
        self.base_url = BASE_URL
        # 置顶状态变量
        self.is_always_on_top = True

        # 设置窗口标志，包括置顶功能
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)

        self.init_ui_elements() # 创建 UI 元素
        self.load_weather_data()

        # 可以保留定时器但默认不启动
        self.raise_timer = QTimer(self)
        self.raise_timer.setInterval(1000)  
        self.raise_timer.timeout.connect(self.bring_to_front)
        # 不再默认启动定时器，因为使用了窗口标志
        # self.raise_timer.start()

    # 分离 UI 元素创建
    def init_ui_elements(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 10, 15, 10)
        self.main_layout.setSpacing(5)

        # ... (创建 QLabel, QHBoxLayout 等 UI 元素 - 代码不变) ...
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.weather_icon_label = QLabel()
        self.weather_icon_label.setText(DEFAULT_EMOJI)
        font_main_emoji = QFont(FONT_FAMILY, 48)
        self.weather_icon_label.setFont(font_main_emoji)
        self.weather_icon_label.setAlignment(Qt.AlignCenter)
        self.weather_icon_label.setFixedSize(64, 64)

        temp_city_layout = QVBoxLayout()
        temp_city_layout.setSpacing(0)
        self.temp_label = QLabel("...")
        font_temp = QFont(FONT_FAMILY, 36, QFont.Bold)
        self.temp_label.setFont(font_temp)
        self.temp_label.setStyleSheet(f"color: {FONT_COLOR.name()};")
        self.city_label = QLabel("...")
        font_city = QFont(FONT_FAMILY, 14)
        self.city_label.setFont(font_city)
        self.city_label.setStyleSheet(f"color: {FONT_COLOR.name()};")
        temp_city_layout.addWidget(self.temp_label)
        temp_city_layout.addWidget(self.city_label)
        temp_city_layout.addStretch()
        top_layout.addWidget(self.weather_icon_label)
        top_layout.addLayout(temp_city_layout)
        top_layout.addStretch()

        self.details_label = QLabel("正在加载...")
        font_details = QFont(FONT_FAMILY, 10)
        self.details_label.setFont(font_details)
        self.details_label.setStyleSheet(f"color: {FONT_COLOR.name()};")

        self.forecast_layout = QHBoxLayout()
        self.forecast_layout.setSpacing(5)
        self.forecast_layout.addStretch()

        self.main_layout.addLayout(top_layout)
        self.main_layout.addWidget(self.details_label)
        self.main_layout.addLayout(self.forecast_layout)

        self.setLayout(self.main_layout)

    # 移除 init_ui 方法
    # def init_ui(self):
    #     ...

    # ... paintEvent, mousePressEvent, mouseMoveEvent ... (不变)
    def paintEvent(self, event):
        """重写paintEvent以绘制圆角背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 抗锯齿
        painter.setBrush(QBrush(BACKGROUND_COLOR))
        painter.setPen(Qt.NoPen) # 无边框
        rect = QRectF(self.rect())
        painter.drawRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def load_weather_data(self):
        """加载天气数据 (使用 OpenWeatherMap API)"""
        # 确保导入 requests 和 json
        import requests
        import json

        complete_url = f"{self.base_url}appid={self.api_key}&q={self.city_name}&units=metric&lang=zh_cn"
        print(f"Fetching weather data from: {complete_url}")

        try:
            response = requests.get(complete_url, timeout=10)
            response.raise_for_status()
            weather_data = response.json()
            print("API Response:", json.dumps(weather_data, indent=2, ensure_ascii=False))

            if weather_data.get("cod") != 200:
                 error_message = weather_data.get("message", "未知API错误")
                 print(f"API Error: {error_message}")
                 self.show_error(f"获取天气失败: {error_message}")
                 # 可以显示上次成功获取的数据或默认值
                 self.update_ui_error_state(f"API错误: {error_message[:30]}...") # 更新UI显示错误
                 return

            # --- 解析数据 ---
            main_data = weather_data.get("main", {})
            weather_info = weather_data.get("weather", [{}])[0]
            wind_data = weather_data.get("wind", {})

            temp = main_data.get("temp")
            humidity = main_data.get("humidity")
            description = weather_info.get("description", "N/A")
            icon_code = weather_info.get("icon", "")
            wind_speed = wind_data.get("speed")
            city = weather_data.get("name", self.city_name)

            # --- 获取对应的 Emoji ---
            weather_emoji = EMOJI_MAP.get(icon_code, DEFAULT_EMOJI)

            # --- 准备传递给UI的数据结构 ---
            ui_data = {
                "temp": f"{temp:.0f}°" if temp is not None else "N/A",
                "city": city,
                # 修改：传递 emoji 而不是 icon_code 或 icon path
                "emoji": weather_emoji,
                "description": description.capitalize(),
                "humidity": f"{humidity}%" if humidity is not None else "N/A",
                "wind_speed": f"{wind_speed}m/s" if wind_speed is not None else "N/A",
                "forecast": [ # 占位符预报 - 需要用实际预报API替换 (使用 Emoji)
                    {"emoji": EMOJI_MAP.get("02d", DEFAULT_EMOJI), "temp": "29°"},
                    {"emoji": EMOJI_MAP.get("10n", DEFAULT_EMOJI), "temp": "26°"},
                    {"emoji": EMOJI_MAP.get("01n", DEFAULT_EMOJI), "temp": "28°"},
                ]
            }
            self.update_ui(ui_data)

        except requests.exceptions.RequestException as e:
            print(f"Network Error: {e}")
            self.show_error(f"网络错误: {e}")
            self.update_ui_error_state(f"网络错误: {str(e)[:30]}...")
        except json.JSONDecodeError:
            print("Error decoding API response")
            self.show_error("无法解析天气数据")
            self.update_ui_error_state("数据错误")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.show_error(f"发生意外错误: {e}")
            self.update_ui_error_state(f"未知错误: {str(e)[:30]}...")

    def update_ui(self, data):
        """根据API数据更新UI元素"""
        self.temp_label.setText(data["temp"])
        self.city_label.setText(data["city"])

        # --- 设置 Emoji ---
        # 修改：设置 Emoji 文本
        self.weather_icon_label.setText(data["emoji"])
        # 移除 Pixmap 相关代码
        # icon_path = ICON_MAP.get(data["icon_code"], DEFAULT_ICON)
        # ... pixmap loading code removed ...
        # self.weather_icon_label.setPixmap(scaled_pixmap)

        self.details_label.setText(f"{data['description']} / 湿度: {data['humidity']} / 风速: {data['wind_speed']}")

        # --- 更新预报 (使用 Emoji) ---
        # 清除旧的预报项
        while self.forecast_layout.count() > 1: # 保留最后的 stretch item
            item = self.forecast_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 添加新的预报项
        for item in data["forecast"]:
            # 修改：传递 emoji
            forecast_widget = WeatherForecastWidget(item["emoji"], item["temp"])
            self.forecast_layout.insertWidget(self.forecast_layout.count() - 1, forecast_widget)

        # 确保元素在切换模式后正确显示/隐藏
        self.details_label.setVisible(not self.is_minimal_mode)
        for i in range(self.forecast_layout.count() -1):
            item = self.forecast_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(not self.is_minimal_mode)
        self.city_label.setVisible(not self.is_minimal_mode)

    def update_ui_error_state(self, message="错误"):
        """更新UI以显示错误状态"""
        self.temp_label.setText("--°")
        self.city_label.setText(self.city_name) # 保留城市名
        self.weather_icon_label.setText("⚠️") # 错误图标
        self.details_label.setText(message)
        # 清除预报
        while self.forecast_layout.count() > 1:
            item = self.forecast_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # --- 移除模拟更新函数 ---
    # def update_weather_mock(self):
    #     ...

    def toggle_minimal_mode(self):
        """切换极简模式"""
        self.is_minimal_mode = not self.is_minimal_mode
        print(f"Toggling minimal mode to: {self.is_minimal_mode}")

        # --- 计算新尺寸和样式 ---
        main_emoji_font_size = 36 if self.is_minimal_mode else 48
        temp_font_size = 24 if self.is_minimal_mode else 36
        window_width = 150 if self.is_minimal_mode else WINDOW_WIDTH
        window_height = 80 if self.is_minimal_mode else WINDOW_HEIGHT
        margins = (10, 5, 10, 5) if self.is_minimal_mode else (15, 10, 15, 10)

        # --- 隐藏/显示元素 ---
        self.details_label.setVisible(not self.is_minimal_mode)
        # 遍历预报布局中的 Widge Items
        for i in range(self.forecast_layout.count()):
            item = self.forecast_layout.itemAt(i)
            widget = item.widget()
            # 确保是 WeatherForecastWidget 实例再隐藏/显示
            if isinstance(widget, WeatherForecastWidget):
                 widget.setVisible(not self.is_minimal_mode)
            # 不要隐藏 Stretch Item
            # elif isinstance(item, QSpacerItem): # Example check if needed
            #     pass
        self.city_label.setVisible(not self.is_minimal_mode)

        # --- 调整样式 ---
        font_main_emoji = QFont(FONT_FAMILY, main_emoji_font_size)
        self.weather_icon_label.setFont(font_main_emoji)
        # 调整图标标签大小以适应字体，或保持固定
        # self.weather_icon_label.adjustSize() # 让标签根据内容调整大小
        # 或者保持固定大小，让Emoji居中
        icon_label_size = 48 if self.is_minimal_mode else 64
        self.weather_icon_label.setFixedSize(icon_label_size, icon_label_size)


        font_temp = QFont(FONT_FAMILY, temp_font_size, QFont.Bold)
        self.temp_label.setFont(font_temp)

        # --- 应用边距 ---
        self.main_layout.setContentsMargins(*margins)

        # --- 最后调整窗口大小 ---
        self.setFixedSize(window_width, window_height)

        # --- 请求重新绘制 ---
        self.update()
        # 移除 self.layout().activate()

    def contextMenuEvent(self, event):
        """添加右键菜单 (示例)"""
        from PySide6.QtWidgets import QMenu

        context_menu = QMenu(self)

        # --- 切换极简模式 ---
        minimal_action_text = "显示完整模式" if self.is_minimal_mode else "切换极简模式"
        minimal_action = QAction(minimal_action_text, self)
        minimal_action.triggered.connect(self.toggle_minimal_mode)
        context_menu.addAction(minimal_action)

        # --- 切换始终置顶 ---
        always_on_top_action = QAction("始终置顶", self, checkable=True)
        always_on_top_action.setChecked(self.is_always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        context_menu.addAction(always_on_top_action)

        context_menu.addSeparator() # 添加分隔线

        # --- 刷新天气 ---
        refresh_action = QAction("刷新天气", self)
        refresh_action.triggered.connect(self.load_weather_data)
        context_menu.addAction(refresh_action)

        # --- 退出 ---
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        context_menu.addAction(quit_action)

        context_menu.exec(event.globalPos())

    def toggle_always_on_top(self, checked):
        """切换窗口置顶状态"""
        self.is_always_on_top = checked
        print(f"--- 切换置顶状态为: {'启用' if checked else '禁用'} ---")
        
        # 获取当前窗口标志
        flags = self.windowFlags()
        
        # 根据置顶状态修改窗口标志
        if checked:
            # 添加 Qt.WindowStaysOnTopHint 标志
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            # 如果定时器在运行，可以停止它(不再需要)
            if self.raise_timer.isActive():
                self.raise_timer.stop()
        else:
            # 移除 Qt.WindowStaysOnTopHint 标志
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        
        # 重新显示窗口以应用标志变更
        self.show()
        print(f"置顶状态变量: {self.is_always_on_top}")

    def bring_to_front(self):
        """当使用定时器策略时调用此方法"""
        # 此方法可以保留但不再需要频繁调用
        if self.is_always_on_top and self.isVisible():
            self.raise_()

    def show_error(self, message):
        """显示错误消息对话框"""
        # QMessageBox.warning(self, "错误", message)
        print(f"Error Display: {message}") # 暂时打印到控制台


if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont(FONT_FAMILY)
    QApplication.setFont(font)

    # --- 移除图标目录和文件检查 ---
    # import os
    # icons_dir = "icons"
    # ... icon checking code removed ...

    window = SkyPeekWindow()
    window.show()
    sys.exit(app.exec())
