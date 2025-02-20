import os, fnmatch, matplotlib
import numpy as np
from functools import lru_cache
from config import GlobalConfig
# 设置matplotlib正常显示中文和负号
# matplotlib.rcParams['font.sans-serif']=['SimHei']   # 用黑体显示中文
# matplotlib.rcParams['axes.unicode_minus']=False     # 正常显示负号
StandardPlotFig = 1
ComparePlotFig = 2
class rec_family(object):
    def __init__(self, colorC=None, draw_mode='Native', image_path=None, figsize=(12, 6), rec_exclude=[], **kwargs):
        # the list of vars' name (with order), string
        self.name_list = []
        # the list of vars' value sequence (with order), float
        self.line_list = []
        # the list of vars' time sequence (with order), float
        self.time_list = []
        # the list of line plotting handles
        self.line_plot_handle = []
        self.line_plot_handle2 = []
        # subplot list
        self.subplots = {}
        self.subplots2 = {}
        # working figure handle
        self.working_figure_handle = None
        self.working_figure_handle2 = None
        # recent time
        self.current_time = None
        self.time_index = None

        self.smooth_line = False
        self.figsize = figsize
        self.colorC = 'k' if colorC is None else colorC
        self.Working_path = 'Testing-beta'
        self.image_num = -1
        self.draw_mode = draw_mode
        self.rec_exclude = rec_exclude
        self.vis_95percent = True
        self.enable_percentile_clamp = True
        logdir = GlobalConfig.logdir
        self.plt = None
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        if self.draw_mode == 'Web':
            import matplotlib.pyplot as plt, mpld3
            self.html_to_write = '%s/html.html'%logdir
            self.plt = plt; self.mpld3 = mpld3
        elif self.draw_mode =='Native':
            import matplotlib.pyplot as plt
            plt.ion()
            self.plt = plt
        elif self.draw_mode =='Img':
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            self.plt = plt
            self.img_to_write = '%s/rec.jpg'%logdir
            if image_path is not None:
                self.img_to_write = image_path
                self.img_to_write2 = image_path+'.jpg'
        else:
            assert False
            
    def rec_disable_percentile_clamp(self):
        self.enable_percentile_clamp = False

    def rec_enable_percentile_clamp(self):
        self.enable_percentile_clamp = True

    def rec_init(self, colorC=None):
        if colorC is not None: self.colorC = colorC
        return
    
    @lru_cache(500)
    def match_exclude(self, name):
        for n in self.rec_exclude:
            if fnmatch.fnmatch(name, n): return True
        return False

    @lru_cache(500)
    def get_index(self, name):
        return self.name_list.index(name)

    def rec(self, var, name):
        if self.match_exclude(name):
            # if var is backlisted
            return
            
        if name in self.name_list:
            # if var is already known, skip
            pass
        else:
            # if var is new, prepare lists
            self.name_list.append(name)
            self.line_list.append([])  #新建一个列表
            self.time_list.append([])
            self.line_plot_handle.append(None)
            self.line_plot_handle2.append(None)
        
        # get the index of the var
        index = self.get_index(name)

        if name=='time': 
            # special var: time
            self.current_time = var
            if self.time_index is None:
                self.time_index = index
            else:
                assert self.time_index == index
        else:
            # normal vars: if time is available, add it
            if self.time_index is not None:
                if len(self.line_list[index]) != len(self.time_list[index]):
                    self.handle_missing_time(self.line_list[index], self.time_list[index])
                self.time_list[index].append(self.current_time)

        # finally, add var value
        self.line_list[index].append(var)

    def handle_missing_time(self, line_arr, time_arr):
        assert len(line_arr) > len(time_arr)
        for i in range(len(line_arr) - len(time_arr)):
            time_arr.append(self.current_time - i - 1)
    
    # This function is ugly because it is translated from MATLAB
    def rec_show(self):
        # the number of total subplots | 一共有多少条曲线
        image_num = len(self.line_list)
        
        if self.working_figure_handle is None:
            self.working_figure_handle = self.plt.figure(StandardPlotFig, figsize=self.figsize, dpi=100)
            if self.draw_mode == 'Native': 
                self.working_figure_handle.canvas.set_window_title(self.Working_path)
                self.plt.show()
        
        # default row=1
        rows = 1

        # check whether the time var exists 检查是否有时间轴，若有，做出修改
        time_var_met = [False] # time_var_met is list because we need it to be mutable | 有时间轴
        time_explicit = ('time' in self.name_list)
        if time_explicit:
            assert self.time_index == self.get_index('time')
            image_num_to_show = image_num - 1
        else:
            image_num_to_show = image_num

        if image_num_to_show >= 3:
            rows = 2 #大与3张图，则放2行
        if image_num_to_show > 8:
            rows = 3 #大与8张图，则放3行
        if image_num_to_show > 12:
            rows = 4 #大与12张图，则放4行
        
        cols = int(np.ceil(image_num/rows)) #根据行数求列数
        if self.image_num!=image_num:
            # 需要刷新布局，所有已经绘制的图作废
            self.subplots = {}
            self.working_figure_handle.clf()
            for q,handle in enumerate(self.line_plot_handle): 
                self.line_plot_handle[q] = None

        self.image_num = image_num
        self.plot_classic(image_num, rows, time_explicit, time_var_met, self.time_index, cols)
            
        # plt.draw()
        # ##################################################
        # ##################################################
        

        # #画重叠曲线，如果有的话
        draw_advance_fig = False
        for name in self.name_list:
            if 'of=' in name: draw_advance_fig = True

        # draw advanced figure, current disabled
        if draw_advance_fig:
            self.plot_advanced()

        # now end, output images
        self.plt.tight_layout()
        if self.draw_mode == 'Web':
            content = self.mpld3.fig_to_html(self.working_figure_handle)
            with open(self.html_to_write, 'w+') as f:
                f.write(content)
            return
        elif self.draw_mode == 'Native':
            self.plt.pause(0.01)
            return
        elif self.draw_mode == 'Img':
            if self.working_figure_handle is not None: 
                self.working_figure_handle.savefig(self.img_to_write)
            if self.working_figure_handle2 is not None: 
                self.working_figure_handle2.savefig(self.img_to_write2)

    def plot_advanced(self):
        #画重叠曲线，如果有的话
        if self.working_figure_handle2 is None:
            self.working_figure_handle2 = self.plt.figure(ComparePlotFig, figsize=self.figsize, dpi=100)
            if self.draw_mode == 'Native': 
                self.working_figure_handle2.canvas.set_window_title('Working-Comp')
                self.plt.show()
        
        group_name = []
        group_member = []
        time_explicit = ('time' in self.name_list)
        
        image_num = len(self.line_list)
        for index in range(image_num):
            if 'of=' not in self.name_list[index]:
                #没有的直接跳过
                continue
            # 找出组别
            g_name_ = self.name_list[index].split('of=')[0]
            if g_name_ in group_name:
                i = group_name.index(g_name_)
                group_member[i].append(index)
            else:
                group_name.append(g_name_)
                group_member.append([index])

        
        num_group = len(group_name)
        image_num_multi = num_group
        rows = 1
        if image_num_multi >= 3:
            rows = 2 #大与3张图，则放2行
        if image_num_multi > 8:
            rows = 3 #大与8张图，则放3行
        if image_num_multi > 12:
            rows = 4 #大与12张图，则放4行
        
        cols = int(np.ceil(image_num_multi/rows))#根据行数求列数
        
        for i in range(num_group):

            subplot_index = i+1
            subplot_name = '%d,%d,%d'%(rows,cols,subplot_index)
            if subplot_name in self.subplots2: 
                target_subplot = self.subplots2[subplot_name]
            else:
                target_subplot = self.working_figure_handle2.add_subplot(rows,cols,subplot_index)
                self.subplots2[subplot_name] = target_subplot

            tar_true_name=group_name[i]
            num_member = len(group_member[i])
            
            for j in range(num_member):
                index = group_member[i][j]
                if time_explicit:
                    # _xdata_ = np.array(self.line_list[time_index], dtype=np.double)
                    _xdata_ = np.array(self.time_list[index], dtype=np.double)

                name_tmp = self.name_list[index]
                name_tmp = name_tmp.replace('=',' ')
                if self.smooth_line:
                    target = smooth(self.line_list[index],20) 
                else:
                    target = self.line_list[index]
                if (self.line_plot_handle2[index] is None):
                    if time_explicit:
                        self.line_plot_handle2[index], =  target_subplot.plot(_xdata_, self.line_list[index],lw=1,label=name_tmp)
                    else:
                        self.line_plot_handle2[index], =  target_subplot.plot(self.line_list[index], lw=1, label=name_tmp)

                else:
                    if time_explicit:
                        self.line_plot_handle2[index].set_data((_xdata_, self.line_list[index]))
                    else:
                        xdata = np.arange(len(self.line_list[index]), dtype=np.double)
                        ydata = np.array(self.line_list[index], dtype=np.double)
                        self.line_plot_handle2[index].set_data((xdata,ydata))

            #标题
            target_subplot.set_title(tar_true_name)
            target_subplot.set_xlabel('time')
            target_subplot.set_ylabel(tar_true_name)
            target_subplot.relim()

            limx1 = target_subplot.dataLim.xmin
            limx2 = target_subplot.dataLim.xmax
            limy1 = target_subplot.dataLim.ymin
            limy2 = target_subplot.dataLim.ymax
            # limx1,limy1,limx2,limy2 = target_subplot.dataLim
            if limx1 != limx2 and limy1!=limy2:
                meany = limy1/2 + limy2/2
                limy1 = (limy1 - meany)*1.2+meany
                limy2 = (limy2 - meany)*1.2+meany
                target_subplot.set_ylim(limy1,limy2)
                meanx = limx1/2 + limx2/2
                limx1 = (limx1 - meanx)*1.05+meanx
                limx2 = (limx2 - meanx)*1.05+meanx
                target_subplot.set_xlim(limx1,limx2)
                target_subplot.grid(visible=True)
                target_subplot.legend(loc='best')
            elif limx1 != limx2:
                meanx = limx1/2 + limx2/2
                limx1 = (limx1 - meanx)*1.1+meanx
                limx2 = (limx2 - meanx)*1.1+meanx
                target_subplot.set_xlim(limx1,limx2)

    def plot_classic(self, image_num, rows, time_explicit, time_var_met, time_index, cols):
        for index in range(image_num):
            if time_explicit:
                if time_index == index:
                    time_var_met[0] = True 
                    # skip time var
                    continue
            # 有时间轴时，因为不绘制时间，所以少算一个subplot
            subplot_index = index if time_var_met[0] else index+1
            subplot_name = '%d,%d,%d'%(rows,cols,subplot_index)
            if subplot_name in self.subplots: 
                target_subplot = self.subplots[subplot_name]
            else:
                target_subplot = self.working_figure_handle.add_subplot(rows,cols,subplot_index)
                self.subplots[subplot_name] = target_subplot

            _xdata_ = np.arange(len(self.line_list[index]), dtype=np.double)
            _ydata_ = np.array(self.line_list[index], dtype=np.double)
            if time_explicit:
                # _xdata_ = np.array(self.line_list[time_index], dtype=np.double)
                _xdata_ = np.array(self.time_list[index], dtype=np.double)
            if (self.line_plot_handle[index] is None):# || ~isvalid(self.line_plot_handle[index])):
                    if time_explicit:
                        self.line_plot_handle[index], =  target_subplot.plot(_xdata_, self.line_list[index],lw=1,c=self.colorC)
                    else:
                        self.line_plot_handle[index], =  target_subplot.plot(self.line_list[index], lw=1, c=self.colorC)
                        
            else:
                if time_explicit:
                    self.line_plot_handle[index].set_data((_xdata_, self.line_list[index]))
                else:
                    xdata = np.arange(len(self.line_list[index]), dtype=np.double)
                    ydata = np.array(self.line_list[index], dtype=np.double)
                    self.line_plot_handle[index].set_data((xdata,ydata))

            if 'of=' in self.name_list[index]:
                #把等号替换成空格
                name_tmp = self.name_list[index]
                name_tmp = name_tmp.replace('=',' ')
                target_subplot.set_title(name_tmp)
                target_subplot.set_xlabel('time')
                target_subplot.set_ylabel(name_tmp)
                target_subplot.grid(visible=True)
            else:
                target_subplot.set_title(self.name_list[index])
                target_subplot.set_xlabel('time')
                target_subplot.set_ylabel(self.name_list[index])
                target_subplot.grid(visible=True)

            limx1 = _xdata_.min() #target_subplot.dataLim.xmin
            limx2 = _xdata_.max() #target_subplot.dataLim.xmax
            limy1 = _ydata_.min() #min(self.line_list[index])
            limy2 = _ydata_.max() #max(self.line_list[index])

            if self.enable_percentile_clamp and len(_ydata_)>220 and self.vis_95percent:
                limy1 = np.percentile(_ydata_, 3, interpolation='midpoint') # 3%
                limy2 = np.percentile(_ydata_, 97, interpolation='midpoint') # 97%

            if limx1 != limx2 and limy1!=limy2:
                    # limx1,limy1,limx2,limy2 = target_subplot.dataLim
                meany = limy1/2 + limy2/2
                limy1 = (limy1 - meany)*1.2+meany
                limy2 = (limy2 - meany)*1.2+meany
                target_subplot.set_ylim(limy1,limy2)

                meanx = limx1/2 + limx2/2
                limx1 = (limx1 - meanx)*1.1+meanx
                limx2 = (limx2 - meanx)*1.1+meanx
                target_subplot.set_xlim(limx1,limx2)
            elif limx1 != limx2:
                meanx = limx1/2 + limx2/2
                limx1 = (limx1 - meanx)*1.1+meanx
                limx2 = (limx2 - meanx)*1.1+meanx
                target_subplot.set_xlim(limx1,limx2)


