
import numpy as np
from Utils.point_cloud_utils import *
from View.view import View
from Model.model import Model
from PySide2.QtWidgets import QApplication, QColorDialog
import os.path as osp
from Utils.common_utils import *
from log_sys import *
from PySide2.QtCore import QTimer, Qt
import PySide2
import sys
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette

dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

class Controller():
    def __init__(self) -> None:
        self.app = QApplication([])
        self.view = View()
        self.model = Model()
        self.system_online_mode = False

        # vis log timer
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.monitor_timer)
        self.Timer.start(50)

        self.signal_connect()

        self.curr_frame_index = 0
        self.show_voxel = False
        self.record_screen = False

        self.view.set_spilter_style()
        self.app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyside2", palette = DarkPalette))
        self.revert_user_config()
        send_log_msg(NORMAL, "Qviz 系統开始运行！")


    def signal_connect(self):
        self.view.dock_range_slide.frameChanged.connect(self.update_system_vis)
        self.view.button_select_pointcloud.SelectDone.connect(self.select_pointcloud)
        for key in self.view.image_dock.keys():
            self.view.image_dock[key].SelectDone.connect(self.select_image)

        self.view.ui.linetxt_point_dim.textChanged.connect(self.update_pointsetting_dims)
        self.view.ui.linetxt_xyz_dim.textChanged.connect(self.update_pointsetting_dims)
        self.view.ui.linetxt_wlh_dim.textChanged.connect(self.update_pointsetting_dims)
        self.view.ui.linetxt_color_dim.textChanged.connect(self.update_pointsetting_dims)
        self.view.pointSizeChanged.connect(self.change_point_size)
        self.view.show_voxel_mode.stateChanged.connect(self.change_voxel_mode)
        self.view.checkbox_record_screen.stateChanged.connect(self.change_record_mode)
        self.view.checkbox_show_car.stateChanged.connect(self.show_car_mode)
        self.view.ui.listwidget_id_color_map.itemDoubleClicked.connect(self.toggle_list_kind_color)

    def revert_user_config(self):
        self.update_pointsetting_dims()
        self.view.revet_layout_config()
        try:
            self.update_system_vis(0)
        except:
            pass
        send_log_msg(NORMAL, "加载配置结束，如果未能显示上一次数据，请检查文件路径或本地资源是否正常")

    def show_car_mode(self, state):
        flag = state > 0
        self.view.set_car_visible(flag)

    def change_record_mode(self, state):
        if state > 0:
            self.record_screen = True
            send_log_msg(NORMAL, "开始录屏")
        else:
            self.record_screen = False
            send_log_msg(NORMAL, "关闭录屏")

    def change_voxel_mode(self, state):
        if state > 0:
            self.show_voxel = True
            send_log_msg(NORMAL, "当前是体素模式")
        else:
            self.show_voxel = False
            send_log_msg(NORMAL, "当前是点云模式")
        self.view.set_voxel_mode(self.show_voxel)
        self.update_buffer_vis()


    def change_point_size(self, ptsize):
        self.update_buffer_vis()

    def toggle_list_kind_color(self):
        dlg = QColorDialog()
        dlg.setWindowFlags(self.view.ui.windowFlags() | PySide2.QtCore.Qt.WindowStaysOnTopHint)

        item = self.view.ui.listwidget_id_color_map.currentItem()
        if dlg.exec_():
            cur_color = dlg.currentColor()
            if item.background().color() != cur_color:
                item.setBackground(cur_color)
                self.view.update_color_map(item.text(), cur_color.name())
                self.update_buffer_vis()

    def select_image(self, topic_path, meta_form):
        send_log_msg(NORMAL, "亲，你选择了图像topic为: %s"%topic_path)
        if self.system_online_mode:
            pass
        else:
            cnt = self.model.deal_image_folder(topic_path, meta_form)
            self.view.set_data_range(self.model.data_frame_list)
            if cnt:
                self.update_system_vis(0)

    def select_pointcloud(self, topic_path, meta_form):
        send_log_msg(NORMAL, "亲，你选择了点云topic为: %s"%topic_path)
        if self.system_online_mode:
            pass
        else:
            cnt = self.model.deal_pointcloud_folder(topic_path, meta_form)
            self.view.set_data_range(self.model.data_frame_list)
            if cnt:
                self.update_system_vis(0)

    def select_lane3d(self,  topic_path, meta_form):
        send_log_msg(NORMAL, "亲，你选择了lane3d的topic为: %s"%topic_path)
        if self.system_online_mode:
            pass
        else:
            pass

    def update_pointsetting_dims(self):
        try:
            self.points_dim, self.xyz_dims, self.wlh_dims, self.color_dims = self.view.get_pointsetting()
        except:
            print(self.points_dim, self.xyz_dims, self.wlh_dims, self.color_dims)
        self.update_buffer_vis()

    def update_buffer_vis(self):
        data_dict = self.model.curr_frame_data
        for meta_form, data in data_dict.items():
            topic_type = self.model.topic_path_meta[meta_form]
            fun_name = topic_type + "_callback"
            callback_fun = getattr(self, fun_name, None)
            callback_fun(data, meta_form, meta_form)

    def update_system_vis(self, index):
        self.curr_frame_index = index
        self.model.get_curr_frame_data(index, self.points_dim)
        self.update_buffer_vis()
        self.view.send_update_vis_flag()
        if self.record_screen:
            self.view.grab_form(self.model.data_frame_list[index] + ".png")

    def run(self):
        self.view.show()
        self.app.exec_()
        self.view.save_layout_config()

    def monitor_timer(self):
        get_msg = ret_log_msg()
        if get_msg != []:
            self.view.dock_log_info.display_append_msg_list(get_msg)

    def sigint_handler(self, signum = None, frame = None):
        self.view.save_layout_config()
        sys.exit(self.app.exec_())


    def image_callback(self, msg, topic, meta_form):
        self.view.set_image(msg, meta_form)

    def pointcloud_callback(self, msg, topic, meta_form):
        max_dim = msg.shape[-1]
        if max(self.xyz_dims) >= max_dim:
            send_log_msg(ERROR, "xyz维度无效:%s,最大维度为%d"%(str(self.xyz_dims, max_dim)))
            return
        points = msg[...,self.xyz_dims]

        if len(self.color_dims) <= 0 or min(self.color_dims) < 0 or max(self.color_dims) >= max_dim:
            send_log_msg(ERROR, "color维度无效:%s,最大维度为%d"%(str(self.color_dims), max_dim))
            color_id_list = -1
        else:
            color_id_list = msg[..., self.color_dims].astype(np.uint8)

        real_color, state = self.view.color_id_to_color_list(color_id_list)

        if not state and max(self.color_dims) != -1:
            send_log_msg(ERROR, "获取颜色维度失败，使用默认颜色")

        if self.show_voxel:
            if len(self.color_dims) <= 0 or min(self.wlh_dims) < 0 or max(self.wlh_dims) > max_dim:
                w = np.ones((len(points), 1)) * 0.4
                l = np.ones((len(points), 1)) * 0.4
                h = np.ones((len(points), 1)) * 0.4
            else:
                w = msg[..., self.wlh_dims[0]]
                l = msg[..., self.wlh_dims[1]]
                h = msg[..., self.wlh_dims[2]]
            if isinstance(real_color, str):
                real_color = np.array([self.view.color_str_to_rgb(real_color)] * len(points))
            self.view.set_point_voxel(points, w, l, h, real_color)
        else:
            self.view.set_point_cloud(points, color = real_color,
                        size=self.view.point_size)
        # print(points.shape)
