"""
This code is based on the demo of Eli Bendersky (eliben@gmail.com)
on the drawing of dynamic mpl (matplotlib)  plot in a wxPython application.
"""
import os
import wx
import serial
import serial.tools.list_ports
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas
import numpy as np
import pylab

# baud rate definition
baud = 1000000
# resistor divider coefficient
k = 1
#max number of acquired samples
MAX_SAMPLES_NUMBER = 8000

class MainWindow(wx.Frame):
    title = 'Ligthweight Arduino Mega 2560 Scope '
    def __init__(self):
        #dpi of the plot
        self.dpi = 100
        #font size for the plot
        font = 8
        self.data_adjust=[]
        #flag for the one shot mode
        self.ch1_one_shot = False
        self.ch1_one_shot_print = False
        #flag for the trigger
        self.ch1_trigger = False
        #initial volt/div
        self.start_voltdiv = 1
        #initial trigger level
        self.level = 2.50*256/5
        #initial delay
        self.delay = 0
        #start with rising edge
        self.edge = 1
        self.end_index = MAX_SAMPLES_NUMBER
        self.right_index = 0
        self.init_index = 0
        self.ch1_paused = False
        self.request = True
        self.port_open = False
        self.count = 0
        self.left_index = 0
        #window dimension x,y
        self.size = (1050,500)
        wx.Frame.__init__(self, None, -1, self.title,(0,0),self.size)
        #center in the screen
        self.Center()
        #create new panel
        self.fig = Figure((7.0, 4.5), dpi=self.dpi)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title('Channel 1', size=font)
        pylab.setp(self.axes.get_xticklabels(), fontsize=font)
        pylab.setp(self.axes.get_yticklabels(), fontsize=font)
        self.axes.grid(True, color='gray')
        self.axes.set_xticks(range(0,MAX_SAMPLES_NUMBER)[::MAX_SAMPLES_NUMBER/10])
        self.canvas = FigCanvas(self, -1, self.fig)
        left  = 0.125  # the left side of the subplots of the figure
        right = 0.9    # the right side of the subplots of the figure
        bottom = 0.1   # the bottom of the subplots of the figure
        top = 0.9      # the top of the subplots of the figure
        wspace = 0.2   # the amount of width reserved for blank space between subplots
        hspace = 0.5   # the amount of height reserved for white space between subplots
        self.fig.subplots_adjust(left, bottom, right, top, wspace, hspace)
        self.panel = wx.Panel(self,-1,(700,0),(325,450))
        #block position
        ch1_conf_x = 10
        ch1_conf_y = 0
        self.ch1_conf_box = wx.StaticBox(self.panel,-1,"Ch1",(ch1_conf_x,ch1_conf_y),(300,435))
        
        #time division control
        ch1_timediv_x = ch1_conf_x + 20
        ch1_timediv_y = ch1_conf_y + 25
        self.timediv_ch1_box = wx.StaticBox(self.panel,-1,"Time/Div ",(ch1_timediv_x, ch1_timediv_y),(130,75))
        self.timediv_ch1 = wx.Choice(self.panel, -1,pos = (ch1_timediv_x + 20, ch1_timediv_y + 20), size = (60, 60),
                                    choices = ["13us","39us","65us","130us","325us","650us","1ms","1.4ms","1.95ms","2.6ms","3.9ms","4.16ms","5.2ms","5.7ms","7.8ms","10.4ms","15.6ms","20.8ms","31.2ms","41.6ms","52ms","62.4ms","72.8ms","83.2ms"])
        self.timediv_ch1.SetSelection(0) 
        self.Bind(wx.EVT_CHOICE, self.time_div_adjust, self.timediv_ch1)
        
        #volt division control
        ch1_voltdiv_x = ch1_timediv_x + 135
        ch1_voltdiv_y = ch1_timediv_y
        self.voltdiv_ch1_box = wx.StaticBox(self.panel,-1,"Volt/Div ",(ch1_voltdiv_x, ch1_voltdiv_y),(130,75))
        self.voltdiv_ch1 = wx.Choice(self.panel, -1,pos = (ch1_voltdiv_x + 20, ch1_voltdiv_y + 20), size = (60, 60),
                                    choices = ["1V","0.5V","0.2V"])
        self.voltdiv_ch1.SetSelection(0) 
        self.Bind(wx.EVT_CHOICE, self.volt_div_adjust, self.voltdiv_ch1)
        
        #trigger level control
        ch1_trigger_x = ch1_timediv_x
        ch1_trigger_y = ch1_timediv_y + 80
        self.trigger_ch1_box = wx.StaticBox(self.panel,-1,"Trigger Level",(ch1_trigger_x, ch1_trigger_y),(130,130))
        self.trigger_level_ch1 = wx.SpinCtrlDouble(self.panel, -1,"2.50",(ch1_trigger_x + 20,ch1_trigger_y + 20),(80,20),min=0,max = 5,inc= 0.01,initial = 2.50)
        self.trigger_level_ch1.SetDigits(2)
        self.Bind(wx.EVT_SPINCTRLDOUBLE , self.on_trigger_level_ch1, self.trigger_level_ch1)
        
        #trigger mode control        
        running_mode_x = ch1_trigger_x + 135
        running_mode_y = ch1_trigger_y
        self.ch1_running_mode_box = wx.StaticBox(self.panel,-1,"Mode ",(running_mode_x, running_mode_y),(130,130))
        self.ch1_mode_free = wx.RadioButton(self.panel, -1, 
            "Free",(running_mode_x + 10,running_mode_y+25),style=wx.RB_GROUP)
        self.ch1_mode_trigger = wx.RadioButton(self.panel, -1,
            "Trigger",(running_mode_x + 10,running_mode_y + 50))
        self.ch1_mode_one_shot = wx.RadioButton(self.panel, -1,
            "One Shot",(running_mode_x + 10,running_mode_y + 75))
            
        self.Bind(wx.EVT_RADIOBUTTON , self.on_ch1_running_mode, self.ch1_mode_trigger)
        self.Bind(wx.EVT_RADIOBUTTON , self.on_ch1_running_mode, self.ch1_mode_free)
        self.Bind(wx.EVT_RADIOBUTTON , self.on_ch1_running_mode, self.ch1_mode_one_shot)   
      
        #edge control
        edge_x = ch1_trigger_x 
        edge_y = ch1_trigger_y + 135
        self.ch1_edge = wx.StaticBox(self.panel,-1,"Edge ",(edge_x, edge_y),(130,130))
        self.ch1_rising_edge = wx.RadioButton(self.panel, -1, 
            "Rising",(edge_x + 10,edge_y + 25),style=wx.RB_GROUP)
        self.ch1_falling_edge = wx.RadioButton(self.panel, -1,
            "Falling",(edge_x + 10,edge_y + 50))
        self.Bind(wx.EVT_RADIOBUTTON , self.on_ch1_edge, self.ch1_rising_edge)
        self.Bind(wx.EVT_RADIOBUTTON , self.on_ch1_edge, self.ch1_falling_edge)
       
        #trigger delay control
        trigger_delay_x = edge_x + 135
        trigger_delay_y = edge_y 
        self.ch1_trigger_delay_box = wx.StaticBox(self.panel,-1,"Delay ",(trigger_delay_x, trigger_delay_y),(130,130))
        self.ch1_trigger_delay =  wx.Slider(self.panel,-1,0,0,90,(trigger_delay_x + 20,trigger_delay_y + 20),(100,100),  wx.SL_HORIZONTAL| wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.ch1_trigger_delay.SetTickFreq(25,25)
        scroll_x = trigger_delay_x + 25
        self.ch1_scroll_right = wx.Button(self.panel, -1, ">",(scroll_x+50,trigger_delay_y + 90),size=(30,20))        
        self.ch1_scroll_left = wx.Button(self.panel, -1, "<",(scroll_x,trigger_delay_y + 90),size=(30,20))  
        self.Bind(wx.EVT_SCROLL, self.on_ch1_trigger_delay, self.ch1_trigger_delay)
        
        #pause button
        self.ch1_pause_button = wx.Button(self.panel, -1, "Pause",(ch1_trigger_x + 15,ch1_trigger_y + 70))
        self.Bind(wx.EVT_BUTTON, self.on_ch1_pause_button, self.ch1_pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_ch1_update_pause_button, self.ch1_pause_button)  
        self.Bind(wx.EVT_BUTTON, self.on_ch1_scroll_right, self.ch1_scroll_right)
        self.Bind(wx.EVT_BUTTON, self.on_ch1_scroll_left, self.ch1_scroll_left) 
        
        #init plot
        self.ch1_screen_data = np.zeros(MAX_SAMPLES_NUMBER)
        self.ch1_plot = self.axes.plot(self.ch1_screen_data,linewidth=1,color=(1, 1, 0))[0]
        self.redraw_timer = wx.Timer(self)
        
        #redraw plot every 50ms
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(50) #ms
  
        #creation of the main menu
        self.create_menu()

    def on_ch1_scroll_right(self, event):
        if(self.right_index < MAX_SAMPLES_NUMBER):       
            self.data_adjust = self.data_adjust[1:len(self.data_adjust)]
            self.data_adjust.extend(self.data[self.right_index:self.right_index+1])
            self.right_index = self.right_index + 1
            self.init_index = self.init_index + 1
            self.end_index = self.end_index + 1
            self.ch1_plot.set_xdata(np.arange(self.init_index,self.end_index))
            self.ch1_plot.set_ydata(np.array(self.data_adjust))
            self.axes.set_ybound(lower=-0.5, upper=5.5)
            self.axes.set_xticks(range(self.init_index,self.end_index)[::(self.end_index-self.init_index)/10])
            self.axes.set_xbound(self.init_index, self.end_index-1)
            self.canvas.draw()
            
    def on_ch1_scroll_left(self, event):
        if(self.left_index > 1):
            self.data_adjust = self.data_adjust[0:len(self.data_adjust)-1]
            self.data_adjust.insert(0,self.data[self.left_index-1])
            self.left_index = self.left_index -1
            self.init_index = self.init_index - 1
            self.end_index = self.end_index - 1          
            self.volt_div_adjust(None)         
            self.ch1_plot.set_xdata(np.arange(self.init_index,self.end_index))
            self.ch1_plot.set_ydata(np.array(self.data_adjust))
            self.axes.set_xticks(range(self.init_index,self.end_index)[::(self.end_index-self.init_index)/10])
            self.axes.set_xbound(self.init_index, self.end_index-1)
            self.axes.set_ybound(lower=-0.5, upper=5.5)
            self.canvas.draw()
            
    def on_ch1_pause_button(self, event):
        self.ch1_paused = not self.ch1_paused
    
    def on_ch1_update_pause_button(self, event):
        label = "Resume" if self.ch1_paused else "Pause"
        self.ch1_pause_button.SetLabel(label)
        
    def on_ch1_trigger_delay(self,event):
        self.delay = self.ch1_trigger_delay.GetValue()
        self.delay = (self.delay*(MAX_SAMPLES_NUMBER-1)/100)+1
        
    def on_ch1_running_mode(self,event):
        self.request = True
        if(self.ch1_mode_trigger.GetValue() == True):
            self.ch1_trigger = True
            self.ch1_one_shot = False
            self.ch1_one_shot_print = False
        elif(self.ch1_mode_free.GetValue() == True):
            self.ch1_trigger = False
            self.ch1_one_shot = False
            self.ch1_one_shot_print = False
            self.ser.close()
            self.ser.open()
        elif(self.ch1_mode_one_shot.GetValue() == True):
            self.ch1_trigger = True
            self.ch1_one_shot = True
            self.ch1_one_shot_print = False
        
    def on_trigger_level_ch1(self,event):
        self.level = self.trigger_level_ch1.GetValue()
        self.level = self.level*256/5
    
    def on_ch1_edge(self,event):
        if(self.ch1_falling_edge.GetValue() == True):
            self.edge = 2
        elif(self.ch1_rising_edge.GetValue() == True):
            self.edge = 1

    def create_menu(self):
        #main menu creation
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        m_expt_csv = menu_file.Append(-1, "&Export Plot", "Export Plot")
        self.Bind(wx.EVT_MENU, self.on_export_plot, m_expt_csv)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)
        
        menu_port = wx.Menu()
       
        ports = list(serial.tools.list_ports.comports())
        self.port_num = len(ports) 
        self.port = []
        self.ports = ports
        i = 0
        for p in ports:
             self.port.append(menu_port.AppendRadioItem(-1, p[0] ))
             self.Bind(wx.EVT_MENU, self.port_selection, self.port[i])
             i = i + 1
        disconnect = menu_port.AppendRadioItem(-1, "Disconnect")
        disconnect.Check()
        self.Bind(wx.EVT_MENU, self.port_disconnect, disconnect)
        self.menubar.Append(menu_port, "&Connect")

    def port_selection(self,event):
        #get the selected port
        for i in range(0,len(self.port)):
            if(self.port[i].IsChecked()):
                if(self.port_open == True):
                    self.ser.close()
                    self.request = True
                self.ser = serial.Serial()
                self.ser.baudrate = baud
                self.ser.port = int(self.ports[i][0].split("COM")[1])-1
                self.ser.timeout = 1
                self.ser.open()
                self.port_open = True

    def port_disconnect(self,event):
         if(self.port_open == True):
             self.ser.close()
             self.port_open = False
             self.request = True
             
    def create_main_panel(self):
        self.panel = wx.Panel(self)

    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()
          
    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)

    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
            
    def on_export_plot(self,event):
        file_choices = "CSV (*csv)|*.csv"
        dlg = wx.FileDialog(
            self, 
            message="Export plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.csv",
            wildcard=file_choices,
            style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            outFile = open(path, 'w')
            outFile.write("Time,Volt\n")
            for i in range(len(self.data_adjust)):
                outFile.write(str(i) + ",")
                outFile.write(str(self.data_adjust[i]) + "\n")
            outFile.close()
            
    def UpdatePlot(self):
        self.time_div_adjust(None)
        self.volt_div_adjust(None)   
        self.print_plot(self.init_index,self.end_index,self.step)
        self.axes.set_ybound(lower=-0.5, upper=5.5)
        self.canvas.draw()
        
    def on_redraw_timer(self, event):
        if(self.port_open == True):
            if(self.ch1_paused == False):
                #free mode
                if (self.ch1_trigger == False):
                    if (self.request == True):
                        self.delay = 0
                        self.ser.write("\xAA")
                              
                        #frequncy dependency
                        if(self.timediv_ch1.GetSelection() <= 15):
                            self.ser.write("\x01")
                        elif(self.timediv_ch1.GetSelection() <= 17):
                            self.ser.write("\x02")
                        elif(self.timediv_ch1.GetSelection() <= 19):
                            self.ser.write("\x03")
                        elif(self.timediv_ch1.GetSelection() > 19):
                            self.ser.write("\x04")
                        self.ser.write("\x00")
                        self.ser.write("\x00")
                        self.ser.write("\x00")
                        ack = self.ser.read(1)
                        while int(ack.encode('hex'),16) != 204:
                            ack = self.ser.read(1)
                            if(ack == ""):
                                ack = "0"
                        self.request = False
                        ack = self.ser.read(1)
                        if(ack == ""):
                                ack = "0"
                        while int(ack.encode('hex'),16) != 204:
                            ack = self.ser.read(1)
                            if(ack == ""):
                                ack = "0"
                        if(int(ack.encode('hex'),16) == 204):
                            self.ser.write("\xEE")
                            data = self.ser.read(MAX_SAMPLES_NUMBER)
                            self.data = []
                            for i in range(0,MAX_SAMPLES_NUMBER):
                                self.data.append(k*int(data[i].encode("hex"),16)*5./256)
                            self.ch1_plot.set_xdata(np.arange(MAX_SAMPLES_NUMBER))
                            self.request = True
                            self.UpdatePlot()
                            self.count = 0
                        else:
                            self.count = self.count + 1
                            if(self.count == 5):
                                self.request = True
                            else:
                                self.request = False
                else:
                    if(self.ch1_one_shot == True and self.ch1_one_shot_print == False):
                        #one shot case
                        if (self.request == True):
                            self.delay = 0
                            self.delay = self.ch1_trigger_delay.GetValue()
                            self.delay = (self.delay*(MAX_SAMPLES_NUMBER-1)/100)+1
                            self.ser.write("\xAA")
                            #frequency dependency
                            if(self.timediv_ch1.GetSelection() <= 15):
                                temp_command = 129
                            elif(self.timediv_ch1.GetSelection() <= 17):
                                temp_command = 130
                            elif(self.timediv_ch1.GetSelection() <= 19):
                                temp_command = 131
                            elif(self.timediv_ch1.GetSelection() > 19):    
                                temp_command = 132
                            if(self.edge == 1):
                                temp_command = temp_command | 16
                            else:
                                temp_command = temp_command | 32
                            self.ser.write(chr(temp_command))
                            
                            #trigger level
                            self.ser.write(chr(int(self.level/k)))
                            delay = "{0:#0{1}x}".format(self.delay,6)
                            self.ser.write(((delay)[len(delay)-4:len(delay)-2]).decode("hex"))
                            self.ser.write(((delay)[len(delay)-2:len(delay)]).decode("hex"))
                            ack = self.ser.read(1)
                            while int(ack.encode('hex'),16) != 204:
                                ack = self.ser.read(1)
                                if(ack == ""):
                                    ack = "0"
                            self.request = False
                            
                        else:
                            #second ack
                            ack = self.ser.read(1)
                            if(ack == ""):
                                ack = "0"
                            if(int(ack.encode('hex'),16) == 204):
                                self.ser.write("\xEE")
                                data = self.ser.read(MAX_SAMPLES_NUMBER)
                                self.data = []
                                for i in range(0,MAX_SAMPLES_NUMBER):
                                    self.data.append(k*int(data[i].encode("hex"),16)*5./256)
                                self.request = True
                                self.ch1_one_shot_print = True
                                self.UpdatePlot()
                            else:
                                self.request = False
                    elif(self.ch1_one_shot_print == False):
                        if(self.request == True):
                            self.delay = 0
                            self.delay = self.ch1_trigger_delay.GetValue()
                            self.delay = (self.delay*MAX_SAMPLES_NUMBER/100)+1
                            self.ser.write("\xAA")
                            #frequncy dependency
                            if(self.timediv_ch1.GetSelection() <= 15):
                                temp_command = 129
                            elif(self.timediv_ch1.GetSelection() <= 17):
                                temp_command = 130
                            elif(self.timediv_ch1.GetSelection() <= 19):
                                temp_command = 131
                            elif(self.timediv_ch1.GetSelection() > 19):    
                                temp_command = 132
                            if(self.edge == 1):
                                temp_command = temp_command | 16
                            else:
                                temp_command = temp_command | 32
                            self.ser.write(chr(temp_command))
                            #trigger level
                            self.ser.write(chr(int(self.level/k)))                      
                            delay = "{0:#0{1}x}".format(self.delay,6)
                            self.ser.write(((delay)[len(delay)-4:len(delay)-2]).decode("hex"))
                            self.ser.write(((delay)[len(delay)-2:len(delay)]).decode("hex"))
                            ack = self.ser.read(1)
                            while int(ack.encode('hex'),16) != 204:
                                ack = self.ser.read(1)
                                if(ack == ""):
                                    ack = "0"
                            self.request = False
                        else:
                            ack = self.ser.read(1)
                            if(ack == ""):
                                ack = "0"
                            if(int(ack.encode('hex'),16) == 204):
                                self.ser.write("\xEE")
                                data = self.ser.read(MAX_SAMPLES_NUMBER)
                                self.data = []
                                for i in range(0,MAX_SAMPLES_NUMBER):
                                    self.data.append(k*int(data[i].encode("hex"),16)*5./256)                
                                self.ch1_one_shot_print = False
                                self.request = True
                                self.UpdatePlot()
                            else:
                                self.request = False

    def volt_div_adjust(self, event):
        if (self.voltdiv_ch1.GetSelection() == 0):
            coef = 1
        elif(self.voltdiv_ch1.GetSelection() == 1):
            coef = 0.5
        elif(self.voltdiv_ch1.GetSelection() == 2):
            coef = 0.2
        self.data_adjust = map(lambda x: x*(1/coef), self.data_adjust)       
        self.start_voltdiv = coef
        
       
    def time_div_adjust(self,event):
        if(self.delay != 0):
            delay = self.delay
        else:
            delay = 0
        #time div selection   
        if (self.timediv_ch1.GetSelection() == 0):
            sample_num = 10
        elif (self.timediv_ch1.GetSelection() == 1):
            sample_num = 30
        elif (self.timediv_ch1.GetSelection() == 2):
            sample_num = 50
        elif (self.timediv_ch1.GetSelection() == 3):
            sample_num = 100
        elif (self.timediv_ch1.GetSelection() == 4):
            sample_num = 250
        elif (self.timediv_ch1.GetSelection() == 5):
            sample_num = 500
        elif (self.timediv_ch1.GetSelection() == 6):        
            sample_num = 800
        elif (self.timediv_ch1.GetSelection() == 7):
            sample_num = 1100 
        elif (self.timediv_ch1.GetSelection() == 8):
            sample_num = 1500
        elif (self.timediv_ch1.GetSelection() == 9):
            sample_num = 2000
        elif (self.timediv_ch1.GetSelection() == 10):
            sample_num = 3000   
        elif (self.timediv_ch1.GetSelection() == 11):
           sample_num = 3200 
        elif (self.timediv_ch1.GetSelection() == 12):
            sample_num = 4000
        elif (self.timediv_ch1.GetSelection() == 13):
            sample_num = 4400
        elif (self.timediv_ch1.GetSelection() == 14 or self.timediv_ch1.GetSelection() == 16 or self.timediv_ch1.GetSelection() == 18 or self.timediv_ch1.GetSelection() == 21):
            sample_num = 6000
        elif (self.timediv_ch1.GetSelection() == 15 or self.timediv_ch1.GetSelection() == 17 or self.timediv_ch1.GetSelection() == 19 or self.timediv_ch1.GetSelection() == 23):
            sample_num = 8000
        elif (self.timediv_ch1.GetSelection() == 20):
            sample_num = 5000
        elif (self.timediv_ch1.GetSelection() == 22):
            sample_num = 7000
        #update the showed data  
        percent = delay*sample_num/(MAX_SAMPLES_NUMBER-2)  
        self.data_adjust = []
        self.data_adjust.extend(self.data[len(self.data)-percent-1:len(self.data)])
        self.data_adjust.extend(self.data[0:sample_num-percent-1])
        self.end_index = sample_num
        self.right_index = sample_num-percent-1
        self.left_index = len(self.data)-percent-1
        self.init_index = 0
        self.step = sample_num/10    
        self.axes.set_ybound(lower=-0.5, upper=5.5)             
            
    def on_exit(self, event):
        self.Destroy()
        
    def print_plot(self,bound_min,bound_max,step):
        self.ch1_plot.set_xdata(np.arange(bound_min,bound_max))
        self.ch1_plot.set_ydata(np.array(self.data_adjust))
        self.axes.set_ybound(lower=-0.5, upper=5.5)
        self.axes.set_xticks(range(bound_min,bound_max)[::step])
        self.axes.set_xbound(bound_min, bound_max-1)
        self.canvas.draw()
        
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(wx.EVT_TIMER,self.on_flash_status_off,self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')

if __name__ == '__main__':
    app = wx.App()
    app.frame = MainWindow()
    app.frame.Show()
    app.MainLoop()