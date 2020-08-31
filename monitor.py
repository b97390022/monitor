#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: bruce
@Co-author: 

Version log:
- 1.0.0 new-release

Next version
- fix on_deleted event.
- fix on_moved event.
- one way sync. (switch mode)
- catch event then call api, update database.
- un-predictable shutdown?
- etc...

"""

__version__ = '1.0.0'

import os
import sys
import stat
import re
import time
import logging
import shutil
import time
import filecmp

from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler

import tkinter as tk
from tkinter import filedialog
import tkinter.scrolledtext as scrolledtext

class Mymonitor(PatternMatchingEventHandler, Observer):
    '''
    Here is the monitor object of watchdog
    '''
    def __init__(self, params, sourcepath, destinationpath, logfunc=print):
        PatternMatchingEventHandler.__init__(self,patterns=params["patterns"],
                                        ignore_patterns=params["ignore_patterns"],
                                        ignore_directories=params["ignore_directories"],
                                        case_sensitive=params["case_sensitive"]
                                        )
        Observer.__init__(self)
        self.schedule(self,path=sourcepath,recursive=True)
        self.schedule(self,path=destinationpath,recursive=True)
        self.sourcepath = sourcepath
        self.destinationpath = destinationpath
        self.timestart = time.asctime(time.localtime(time.time()))
        self.log = logfunc
        
    def on_created(self, event):
        self.log(f"file {event.src_path} has been created!")
        if event.src_path.startswith(self.sourcepath):
            self.copy(event,self.sourcepath,self.destinationpath)
        elif event.src_path.startswith(self.destinationpath): 
            self.copy(event,self.destinationpath,self.sourcepath)

    def on_modified(self, event):
        # this only apply to content modify.
        self.log(f"file {event.src_path} has been modified!")
        if not event.is_directory:
            if event.src_path.startswith(self.sourcepath):
                self.copy(event,self.sourcepath,self.destinationpath)
            elif event.src_path.startswith(self.destinationpath): 
                self.copy(event,self.destinationpath,self.sourcepath)

    def on_moved(self, event):
        # this include rename/moving of files/directories.
        self.log(f"file {event.src_path} moved to {event.dest_path}") 
        

    def on_deleted(self, event):
        # this include deleting/moving of files/directories.
        self.log(f"file {event.src_path} has been deleted!")
        try:
            if event.src_path.startswith(self.sourcepath):
                if event.is_directory:
                    self.log(os.path.abspath(event.src_path))        
                    shutil.rmtree(os.path.abspath(event.src_path).replace(self.sourcepath, self.destinationpath), onerror=remove_readonly)
                else:
                    os.remove(event.src_path.replace(self.sourcepath, self.destinationpath))
            elif event.src_path.startswith(self.destinationpath): 
                if event.is_directory:
                    self.log(os.path.abspath(event.src_path))
                    shutil.rmtree(os.path.abspath(event.src_path).replace(self.destinationpath, self.sourcepath), onerror=remove_readonly)
                else:
                    os.remove(event.src_path.replace(self.destinationpath, self.sourcepath))
        except Exception as e:
            print(f'Error! Code: {type(e).__name__}, Message, {str(e)}')
            pass

        def remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            func(path)

    def copy(self,event,path1,path2):
        if event.is_directory and not os.path.exists(event.src_path.replace(path1, path2)):
            os.makedirs(event.src_path.replace(path1, path2))
        elif not event.is_directory and not os.path.exists(event.src_path.replace(path1, path2)):
            os.makedirs(os.path.dirname(event.src_path.replace(path1, path2)), exist_ok=True)
            shutil.copy2(event.src_path, event.src_path.replace(path1, path2))
        elif not event.is_directory and os.path.exists(event.src_path.replace(path1, path2)):
            if not filecmp.cmp(event.src_path,event.src_path.replace(path1, path2),shallow=False):
                shutil.copy2(event.src_path, event.src_path.replace(path1, path2))

class GUI:
    ''' 
    Here is the GUI
    '''
    def __init__(self,params):
        self.watchdog = None
        self.params = params
        self.sourcepath = '.'
        self.destinationpath = '.'
        self.root = tk.Tk()
        self.label = tk.Label(text="",bg='black',fg='white',font=('consolas', '12'))
        self.label.pack(fill='x')
        self.update_clock()
        self.messagebox = tk.scrolledtext.ScrolledText(width=100, height=20,bg='black',fg='white',undo=True, font=('consolas', '12'))
        self.messagebox.pack()

        self.footer = tk.Label(text=f'Sourcepath: {self.sourcepath}, Destinationpath: {self.destinationpath}',bg='black',fg='white',font=('consolas', '12'))
        self.footer.pack(fill='x')

        frm = tk.Frame(self.root)
        self.root.title("My Monitor")
        self.root.iconbitmap("research.ico")
        tk.Button(frm, text='Select sourcepath', command=lambda: self.select_path(1),height=2).pack(side='left')
        tk.Button(frm, text='Select destinationpath', command=lambda: self.select_path(2),height=2).pack(side='left') 
        tk.Button(frm, text='Sync', command=lambda: PopUpConfirm(self),height=2,width=5).pack(side='left')
        tk.Button(frm, text='Input params', command=lambda: inputParams(self),height=2,width=10).pack(side='right')
        tk.Button(frm, text='Clear', command=self.clear,height=2).pack(side='right')
        tk.Button(frm, text='Stop Watchdog', command=self.stop_watchdog,height=2).pack(side='right')
        tk.Button(frm, text='Start Watchdog', command=self.start_watchdog,height=2).pack(side='right')
        frm.pack(fill='x', expand=1)

        self.root.mainloop()

    def start_watchdog(self):
        # start
        if self.watchdog is None:
            self.watchdog = Mymonitor(params=self.params,sourcepath=self.sourcepath,destinationpath=self.destinationpath, logfunc=self.log)
            self.watchdog.start()
            self.log('Watchdog started!')
        else:
            self.log('Watchdog already started!')

    def stop_watchdog(self):
        # stop
        if self.watchdog:
            self.watchdog.stop()
            self.watchdog.join()
            self.watchdog = None
            self.log('Watchdog stopped!')
        else:
            self.log('Watchdog is not running!')

    def select_path(self,num):
        # select path
        path = filedialog.askdirectory()
        if path and num == 1:
            self.sourcepath = path
            # self.log(f'Selected sourcepath: {path}')
            self.update_footer()
        elif path and num == 2:
            self.destinationpath = path
            # self.log(f'Selected destinationpath: {path}')
            self.update_footer()

    def log(self, message):
        # print on textbox
        self.messagebox.insert('end', f'{message}\n')
        self.messagebox.see('end',)

    def clear(self):
        # clear textbox
        self.messagebox.delete(1.0, "end")

    def update_clock(self):
        now = time.ctime(time.time())
        self.label.configure(text=f'現在時間: {now}')
        self.root.after(1000, self.update_clock)
    
    def update_footer(self):
        self.footer.configure(text=f'Sourcepath: {self.sourcepath}, Destinationpath: {self.destinationpath}')
    

    def sync(self,sourcepath,destinationpath):
        '''
        sync two directories.
        '''
        if not (sourcepath == destinationpath):
            def _dirtree(path):
                '''
                creates list of dirs and files in source and 
                destination
                '''
                returndirs = []
                returnfiles = []

                for root, dirs, files in os.walk(path):
                    for _dir in dirs:
                        abs_dir = os.path.join(root, _dir)
                        returndirs.append(
                                [abs_dir, 
                                os.path.relpath(abs_dir, path)]
                        )
                    for _file in files:
                        abs_f = os.path.join(root, _file)
                        returnfiles.append(
                                [abs_f, 
                                os.path.relpath(abs_f, path)]
                        )
                return (returndirs, returnfiles)

            src_dirs, src_files  = _dirtree(sourcepath)
            dest_dirs, dest_files = _dirtree(destinationpath)

            for src_dir in src_dirs:
                rel_path = src_dir[1]
                equivalent_dest_dir = list(filter(lambda x:x[1] == rel_path, dest_dirs))
                dest_path = os.path.join(destinationpath,rel_path) 
                if len(equivalent_dest_dir) == 0:
                    # if dir is in source but not in destination
                    os.makedirs(dest_path)
                    self.log (f"creating {dest_path}")

            for dest_dir in dest_dirs:
                rel_path = dest_dir[1]
                equivalent_src_dir = list(filter(lambda x:x[1] == rel_path,src_dirs))
                src_path = os.path.join(sourcepath,rel_path)
                if len(equivalent_src_dir) == 0:
                    # if dir is in destination but not source
                    os.makedirs(src_path)
                    self.log (f"creating {src_path}")

            for src_file in src_files:
                rel_path = src_file[1]
                equivalent_dest_file = list(filter(lambda x:x[1] == rel_path,dest_files))
                dest_path = os.path.join(destinationpath,rel_path)
                if len(equivalent_dest_file) == 0:
                    # if the file is in source but not in dest
                    shutil.copy2(src_file[0], dest_path)
                    self.log (f"creating {src_file[0]}")
                elif not filecmp.cmp(equivalent_dest_file[0][0],src_file[0],shallow=False):
                    # if the file between source and dest but has different content
                    src_mtime = time.ctime(os.path.getmtime(src_file[0]))
                    dest_mtime = time.ctime(os.path.getmtime(equivalent_dest_file[0][0]))
                    if src_mtime > dest_mtime:
                        shutil.copy2(src_file[0], dest_path)
                        self.log (f"copy from {src_file[0]} to {dest_path}")
                    else:
                        shutil.copy2(dest_path, src_file[0])
                        self.log (f"copy from {dest_path} to {src_file[0]}")

            for dest_file in dest_files:
                rel_path = dest_file[1]
                equivalent_src_file = list(filter(lambda x:x[1] == rel_path,src_files))
                src_path = os.path.join(sourcepath,rel_path)
                if len(equivalent_src_file) == 0:
                    # if file is in destination but not in source
                    shutil.copy2(dest_file[0], src_path)
                    self.log (f"creating {dest_file[0]}")
                elif not filecmp.cmp(equivalent_src_file[0][0],dest_file[0],shallow=False):
                    # if the file between source and dest but has different content
                    dest_mtime = time.ctime(os.path.getmtime(dest_file[0]))
                    src_time = time.ctime(os.path.getmtime(equivalent_src_file[0][0]))
                    if dest_mtime > src_time:
                        shutil.copy2(dest_file[0], src_path)
                        self.log (f"copy from {dest_file[0]} to {src_path}")
                    else:
                        shutil.copy2(src_path, dest_file[0])
                        self.log (f"copy from {src_path} to {dest_file[0]}")
            self.log('Sync finished!')

class PopUpConfirm(tk.Toplevel):
    # double confirm on sync function
    def __init__(self, master=None):
        super().__init__(master.root)
        self.title("Confirm")
        self.geometry("400x80")
        tk.Label(self, text="Are you sure you want to sync?").pack()
        tk.Button(self, text='Confirm', command=combine_funcs(lambda: master.sync(master.sourcepath, master.destinationpath),self.destroy), fg='red',height=20,width=20).pack(side='left', fill='both', padx=(30, 5), pady=5)
        tk.Button(self, text='No!', command=self.destroy,height=20,width=20).pack(side='right', fill='both', padx=(5, 30), pady=5)

class inputParams(tk.Toplevel):
    # change default Parameters
    def __init__(self, master=None):
        super().__init__(master.root)
        self.title("Input Parameters")
        self.geometry("450x150")
        self.c1 = tk.BooleanVar()
        self.c2 = tk.BooleanVar()
        self.c3 = tk.BooleanVar()
        self.c4 = tk.BooleanVar()
        self.c1.set(False)
        self.c2.set(True)
        self.c3.set(True)
        self.c4.set(False)

        frm = tk.Frame(self)
        tk.Label(frm,text="patterns: e.g \"*\", \".gif\"").grid(row=0, column=1,sticky='w')
        e1 = tk.Entry(frm,bd=5)
        e1.insert('end',master.params["patterns"])
        e1.grid(row=0, column=2,sticky='w')
        tk.Label(frm,text="default: \"*\"").grid(row=0, column=3,sticky='w')

        tk.Label(frm,text="Ignore patterns: e.g \"*\", \".gif\"").grid(row=1, column=1,sticky='w')
        e2 = tk.Entry(frm,bd=5)
        e2.insert('end',master.params["ignore_patterns"])
        e2.grid(row=1, column=2,sticky='w')
        tk.Label(frm,text="default: \"\"").grid(row=1, column=3,sticky='w')

        tk.Label(frm,text="Ignore directories: ").grid(row=2, column=1,sticky='w')
        igdt = tk.Checkbutton(frm,text = "True", variable = self.c1)
        igdt.grid(row=2, column=2,sticky='w')
        igdf = tk.Checkbutton(frm,text = "False", variable = self.c2)
        igdf.grid(row=2, column=2,sticky='w',padx=(70,0))
        tk.Label(frm,text="default: False").grid(row=2, column=3,sticky='w')

        tk.Label(frm,text="Case_sensitive: ").grid(row=3, column=1,sticky='w')
        cst = tk.Checkbutton(frm,text = "True", variable = self.c3)
        cst.grid(row=3, column=2,sticky='w')
        csf = tk.Checkbutton(frm,text = "False", variable = self.c4)
        csf.grid(row=3, column=2,sticky='w',padx=(70,0))
        tk.Label(frm,text="default: True").grid(row=3, column=3,sticky='w')

        tk.Button(frm, text='Input', command=combine_funcs(lambda: self.update_params(master,e1,e2),self.destroy), fg='red',height=1,width=10).grid(row=4, column=2,sticky='w', padx=(3, 5), pady=5)
        tk.Button(frm, text='Cancel', command=self.destroy,height=1,width=10).grid(row=4, column=3,sticky='w', padx=(5, 30), pady=5)
        frm.grid()

    def update_params(self,master,e1,e2):
        master.params["patterns"] = list(e1.get())
        master.params["ignore_patterns"] = list(e2.get())
        master.params["ignore_directories"] = self.c1.get()
        master.params["case_sensitive"] = self.c3.get()

def combine_funcs(*funcs):
    # combine fuctions for button command
    def combined_func(*args, **kwargs):
        for f in funcs:
            f(*args, **kwargs)
    return combined_func

# def rmtree(top):
#     # remtree with admin but fail?
#     for root, dirs, files in os.walk(top, topdown=False):
#         for name in files:
#             filename = os.path.join(root, name)
#             os.chmod(filename, stat.S_IWUSR)
#             os.remove(filename)
#         for name in dirs:
#             os.rmdir(os.path.join(root, name))
#     os.rmdir(top)    

def main():
    print('Hi, this is to monitor the file directory and compare to remote directory. Type "*help" to get detail instruction. Type "exit" to leave.')
    patterns = list("*")
    ignore_patterns = list("")
    ignore_directories = False
    case_sensitive = True
    params = {"patterns":patterns,"ignore_patterns":ignore_patterns,"ignore_directories":ignore_directories,"case_sensitive":case_sensitive}   
    GUI(params)
        
if __name__ == "__main__":
    main()

    
    
    