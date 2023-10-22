import os
import os.path
import sys
import threading

import requests
from urllib.parse import urlencode

from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import tkinter as tk

from pathlib import Path

# Переменная, задающие размер файла ffmpeg.exe в байтах, и текущий объем скаченного файла

total_size, cur_size = 100827136, 0
path_to_file = ''

main_client = []


# Класс, отображающий процесс применения изменений к видео
# Наследуется от tk.Toplevel - под-окно библиотеки Tkinter


class ExecutionGUI(tk.Toplevel):

    # Запускаем конструктор класса

    def __init__(self, main_gui=None):

        # Класс применения измнений имеет доступ к основному окну
        self.AppGUI = main_gui

        # Основное окно сворачивается
        self.AppGUI.withdraw()

        # Инициализируем класс
        tk.Toplevel.__init__(self)

        self.focus()

        self.focus_set()

        # Начало прописывания основных атрибутов окна
        self.title("Applying ffmpeg changes")

        self.update()
        self.screen_width, self.screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.update()

        self.window_width, self.window_height = 400, 100
        self.geometry("{}x{}+{}+{}".format(self.window_width, self.window_height,
                                           int(self.screen_width / 2 - self.window_width / 2),
                                           int(self.screen_height / 2 - self.window_height / 2)))
        self.resizable(False, False)

        self.iconbitmap('D:\Documents\Python_files\English_video_creator\English_Video_Creator_icon_1.ico')
        self.attributes('-topmost', True)
        # Завершение прописывания основных атрибутов окна

        # Начало указания основных элементов на окне
        self.progressbar_width, self.progressbar_height = 280, 20

        self.download_statues = ttk.Progressbar(self,
                                                orient='horizontal',
                                                mode='indeterminate',
                                                length=100,
                                                value=10,
                                                maximum=100
                                                )

        self.download_statues.place(x=self.window_width / 2 - self.progressbar_width / 2,
                                    y=20,
                                    width=self.progressbar_width,
                                    height=self.progressbar_height)

        self.download_statues.start(20)

        self.Info_label = tk.Label(self, text="Files are being converted by ffmpeg.exe")
        self.Info_label.place(x=self.window_width / 2 - 125,
                              y=40,
                              width=250,
                              height=20)

        self.CurrentTask_label = tk.Label(self, text="")
        self.CurrentTask_label.place(x=self.window_width / 2 - 125,
                                     y=60,
                                     width=250,
                                     height=20)

        self.Wait_label = tk.Label(self, text="Please, Wait")
        self.Wait_label.place(x=self.window_width / 2 - 125,
                              y=80,
                              width=250,
                              height=20)

        # Завершение указания основных элементов на окне

        # Запуск анимации текста
        self.wait_label_action()

        # Запуск потока для обработки преобразования видео
        # Многопоточность требуется, чтобы Tkinter-приложение не зависало при обработке видео
        self.Applying_changes_to_video_thread = threading.Thread(target=self.video_converting, args=())
        self.Applying_changes_to_video_thread.daemon = True
        self.Applying_changes_to_video_thread.setDaemon(True)
        self.Applying_changes_to_video_thread.start()

        # Поток обработки видео активен
        self.thread_active = True

        # Протокол закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.close_download_gui)

        # Цикл-обработчик событий Tkinter
        self.mainloop()

    # При закрытие окна
    def close_download_gui(self):

        # Если поток активен
        if self.thread_active:

            # Выходим из коммандной строки
            os.system('exit')

            # Меняем тексты Label-ов на экране
            self.Info_label.config(text="Canceling the process!")

            # Если работа завершилась не из-за завершения обработки видео, то изменяем label-состояния
            if self.AppGUI.eng_sub_added and not self.AppGUI.rus_sub_added and not self.AppGUI.watermark_added:
                self.CurrentTask_label.config(text="Current task: Removing video with english subs")

            if self.AppGUI.rus_sub_added and not self.AppGUI.eng_sub_added and not self.AppGUI.watermark_added:
                self.CurrentTask_label.config(text="Current task: Removing video with russian subs")

            if self.AppGUI.watermark_added and not self.AppGUI.eng_sub_added and not self.AppGUI.rus_sub_added:
                self.CurrentTask_label.config(text="Current task: Removing video with watermark")

            if self.AppGUI.eng_sub_added and self.AppGUI.rus_sub_added and not self.AppGUI.watermark_added:
                self.CurrentTask_label.config(text="Current task: Removing _temp video")

            if self.AppGUI.eng_sub_added and self.AppGUI.watermark_added and not self.AppGUI.rus_sub_added:
                self.CurrentTask_label.config(text="Current task: Removing _temp video")

            if self.AppGUI.watermark_added and self.AppGUI.rus_sub_added and not self.AppGUI.eng_sub_added:
                self.CurrentTask_label.config(text="Current task: Removing _temp video")

            if self.AppGUI.eng_sub_added and self.AppGUI.rus_sub_added and self.AppGUI.watermark_added:
                self.CurrentTask_label.config(text="Current task: Removing _temp videos")

            self.thread_active = False
            return

        return

    # Добавление анимации при скачивании файла ffmpeg (К слову "Подождите" добавляются точки)

    def wait_label_action(self, counter=0):
        self.Wait_label['text'] += '.'
        counter += 1

        # Начинаем заново

        if counter == 6:
            self.Wait_label['text'] = self.Wait_label['text'][:-6]
            counter = 0

        # Запускаем функцию с переодичностью

        self.after(400, lambda: self.wait_label_action(counter))

    # Функция, непосредственно добавляющая к исходному видео-файлу субтитры и водянной знак

    def video_converting(self):

        # Запускаем второй поток в Python, необходимо, чтобы интерфейс не замораживался во время конвертации

        self.thread_active = True

        # Если только английские субтитры были добавлены пользователем

        if self.AppGUI.eng_sub_added and not self.AppGUI.rus_sub_added and not self.AppGUI.watermark_added:

            # Переназначивает текст текущей исполняемой задачи программы (для удобства использования интерфейса)

            self.CurrentTask_label.config(text="Current task: Adding English subtitles to video")

            # Подгружаем введенные пользователем данные (пути исходного видео, субтитров, выходного видео )

            video_path = self.AppGUI.VideoPath_entry.get()
            eng_sub_path = self.AppGUI.EnglishSub_entry.get()
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            video_path_full = video_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            # Меняем текущую папку на ту, в которой храниться ffmpeg.exe
            # Необходимо, чтобы можно было использовать команды ffmpeg

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            eng_sub_list = eng_sub_path.split('/')
            eng_sub_path_full = eng_sub_list[0][0] + '\\:/' + '/'.join(eng_sub_list[1:])

            # Если мы прервали программу конвертации на этом этапе (закрыли окно преобразования), то

            if not self.thread_active:

                # Возвращаемся на предыдущее окно выбора данных

                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            # Выполняем добавление субтитров к видео

            os.system(
                f'''ffmpeg -i "{video_path_full}" -filter_complex "subtitles='{eng_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{changed_video_path_full}"''')

            # Выполняем функцию exit закрывая терминал

            os.system('exit')

            # Если мы прервали программу конвертации на этом этапе, то

            if not self.thread_active:

                # Выполняем все тоже самое, только еще удаляем получившееся видео

                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

        # Если только английские субтитры были добавлены пользователем, то действия аналогичны
        # за исключением того, что исходные данные субтитров берутся из строки, отведенную под русские субтитры

        if self.AppGUI.rus_sub_added and not self.AppGUI.eng_sub_added and not self.AppGUI.watermark_added:

            self.CurrentTask_label.config(text="Current task: Adding Russian subtitles to video")

            video_path = self.AppGUI.VideoPath_entry.get()
            rus_sub_path = self.AppGUI.RussianSub_entry.get()
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            video_path_full = video_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            rus_sub_list = rus_sub_path.split('/')
            rus_sub_path_full = rus_sub_list[0][0] + '\\:/' + '/'.join(rus_sub_list[1:])

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{video_path_full}" -filter_complex "subtitles='{rus_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{changed_video_path_full}"''')

            os.system('exit')

            if not self.thread_active:
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

        # Если только водянной знак был выбран пользователем, то
        # алгоритм действий аналогичен двум предыдущим, за исключение того, что функция ffmpeg - другая

        if self.AppGUI.watermark_added and not self.AppGUI.eng_sub_added and not self.AppGUI.rus_sub_added:

            self.CurrentTask_label.config(text="Current task: Adding watermark to video")

            video_path = self.AppGUI.VideoPath_entry.get()

            # Путь до изображения водянного знака

            watermark_path = self.AppGUI.WatermarkPath_entry.get()
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            # Выбор значения непрозрачности водянного знака

            watermark_transparency_factor = float(self.AppGUI.TransparencyFactor_scale.get())

            video_path_full = video_path.replace('/', '\\')
            watermark_path_full = watermark_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            # Дабовление водянного знака по центру видео с заданной прозрачностью

            os.system(
                f'ffmpeg -i "{video_path_full}" -i "{watermark_path_full}" -filter_complex "[1]format=rgba,colorchannelmixer=aa={watermark_transparency_factor}[logo];[0][logo]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p" -codec:a copy "{changed_video_path_full}"')

            os.system('exit')

            if not self.thread_active:
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

        # Если пользователь добавил русские и английские субтитры, но не добавил водянной знак

        if self.AppGUI.eng_sub_added and self.AppGUI.rus_sub_added and not self.AppGUI.watermark_added:

            self.CurrentTask_label.config(text="Current task: Adding Russian subtitles to video")

            video_path = self.AppGUI.VideoPath_entry.get()
            rus_sub_path = self.AppGUI.RussianSub_entry.get()
            eng_sub_path = self.AppGUI.EnglishSub_entry.get()
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            video_path_full = video_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            changed_video_name = Path(changed_video_path_full).stem
            temp_file_path_1 = os.path.dirname(changed_video_path_full) + '\\' + changed_video_name + '_temp_1' + '.mp4'

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            rus_sub_list = rus_sub_path.split('/')
            rus_sub_path_full = rus_sub_list[0][0] + '\\:/' + '/'.join(rus_sub_list[1:])

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{video_path_full}" -filter_complex "subtitles='{rus_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{temp_file_path_1}"''')

            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            self.CurrentTask_label.config(text="Current task: Adding English subtitles to video")

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')
            eng_sub_list = eng_sub_path.split('/')
            eng_sub_path_full = eng_sub_list[0][0] + '\\:/' + '/'.join(eng_sub_list[1:])

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{temp_file_path_1}" -filter_complex "subtitles='{eng_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{changed_video_path_full}"''')

            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.remove(f"{temp_file_path_1}")

        # Если пользователь добавил русские субтитры и водянной знак, но не добавил английские субтитры

        if self.AppGUI.rus_sub_added and self.AppGUI.watermark_added and not self.AppGUI.eng_sub_added:

            self.CurrentTask_label.config(text="Current task: Adding Russian subtitles to video")

            video_path = self.AppGUI.VideoPath_entry.get()
            rus_sub_path = self.AppGUI.RussianSub_entry.get()
            watermark_path = self.AppGUI.WatermarkPath_entry.get()
            watermark_transparency_factor = float(self.AppGUI.TransparencyFactor_scale.get())
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            video_path_full = video_path.replace('/', '\\')
            watermark_path_full = watermark_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            changed_video_name = Path(changed_video_path_full).stem
            temp_file_path_1 = os.path.dirname(
                changed_video_path_full) + '\\' + changed_video_name + '_temp_1' + '.mp4'

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            rus_sub_list = rus_sub_path.split('/')
            rus_sub_path_full = rus_sub_list[0][0] + '\\:/' + '/'.join(rus_sub_list[1:])

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{video_path_full}" -filter_complex "subtitles='{rus_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{temp_file_path_1}"''')

            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            self.CurrentTask_label.config(text="Current task: Adding watermark to video")

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'ffmpeg -i "{temp_file_path_1}" -i "{watermark_path_full}" -filter_complex "[1]format=rgba,colorchannelmixer=aa={watermark_transparency_factor}[logo];[0][logo]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p" -codec:a copy "{changed_video_path_full}"')
            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.remove(f"{temp_file_path_1}")

        # Если пользователь добавил английские субтитры и водянной знак, но не добавил русские субтитры

        if self.AppGUI.eng_sub_added and self.AppGUI.watermark_added and not self.AppGUI.rus_sub_added:

            self.CurrentTask_label.config(text="Current task: Adding English subtitles to video")

            video_path = self.AppGUI.VideoPath_entry.get()
            eng_sub_path = self.AppGUI.EnglishSub_entry.get()
            watermark_path = self.AppGUI.WatermarkPath_entry.get()
            watermark_transparency_factor = float(self.AppGUI.TransparencyFactor_scale.get())
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()

            video_path_full = video_path.replace('/', '\\')
            watermark_path_full = watermark_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            changed_video_name = Path(changed_video_path_full).stem
            temp_file_path_1 = os.path.dirname(
                changed_video_path_full) + '\\' + changed_video_name + '_temp_1' + '.mp4'

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            eng_sub_list = eng_sub_path.split('/')
            eng_sub_path_full = eng_sub_list[0][0] + '\\:/' + '/'.join(eng_sub_list[1:])

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{video_path_full}" -filter_complex "subtitles='{eng_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{temp_file_path_1}"''')

            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            self.CurrentTask_label.config(text="Current task: Adding watermark to video")

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'ffmpeg -i "{temp_file_path_1}" -i "{watermark_path_full}" -filter_complex "[1]format=rgba,colorchannelmixer=aa={watermark_transparency_factor}[logo];[0][logo]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p" -codec:a copy "{changed_video_path_full}"')
            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.remove(f"{temp_file_path_1}")

        # Если пользователь добавил русские и английские субтитры и добавил водянной знак, то
        # действия будут выполняться последовательно, на каждом этапе будет создаваться отдельное временнное видео,
        # которое будет выступать исходным при выполнении последующих преобразований

        if self.AppGUI.eng_sub_added and self.AppGUI.rus_sub_added and self.AppGUI.watermark_added:

            self.CurrentTask_label.config(text="Current task: Adding watermark to video")

            video_path = self.AppGUI.VideoPath_entry.get()
            rus_sub_path = self.AppGUI.RussianSub_entry.get()
            eng_sub_path = self.AppGUI.EnglishSub_entry.get()
            watermark_path = self.AppGUI.WatermarkPath_entry.get()
            changed_video_path = self.AppGUI.ChangedVideoPath_entry.get()
            watermark_transparency_factor = float(self.AppGUI.TransparencyFactor_scale.get())

            video_path_full = video_path.replace('/', '\\')
            watermark_path_full = watermark_path.replace('/', '\\')
            changed_video_path_full = changed_video_path.replace('/', '\\')

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            changed_video_name = Path(changed_video_path_full).stem
            temp_file_path_1 = os.path.dirname(changed_video_path_full) + '\\' + changed_video_name + '_temp_1' + '.mp4'

            if not self.thread_active:
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'ffmpeg -i "{video_path_full}" -i "{watermark_path_full}" -filter_complex "[1]format=rgba,colorchannelmixer=aa={watermark_transparency_factor}[logo];[0][logo]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p" -codec:a copy "{temp_file_path_1}"')
            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            self.CurrentTask_label.config(text="Current task: Adding Russian subtitles to video")

            temp_file_path_2 = os.path.dirname(changed_video_path_full) + '\\' + changed_video_name + '_temp_2' + '.mp4'

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')
            rus_sub_list = rus_sub_path.split('/')
            rus_sub_path_full = rus_sub_list[0][0] + '\\:/' + '/'.join(rus_sub_list[1:])
            print(rus_sub_path_full)

            if not self.thread_active:
                os.remove(temp_file_path_1)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{temp_file_path_1}" -filter_complex "subtitles='{rus_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{temp_file_path_2}"''')

            os.system('exit')

            self.CurrentTask_label.config(text="Current task: Adding English subtitles to video")

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(temp_file_path_2)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\')

            eng_sub_list = eng_sub_path.split('/')
            eng_sub_path_full = eng_sub_list[0][0] + '\\:/' + '/'.join(eng_sub_list[1:])

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(temp_file_path_2)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            os.system(
                f'''ffmpeg -i "{temp_file_path_2}" -filter_complex "subtitles='{eng_sub_path_full}'" -c:v libx264 -crf 20 -c:a aac -strict experimental -b:a 192k "{changed_video_path_full}"''')
            os.system('exit')

            if not self.thread_active:
                os.remove(temp_file_path_1)
                os.remove(temp_file_path_2)
                os.remove(changed_video_path_full)
                self.AppGUI.update()
                self.AppGUI.deiconify()
                self.destroy()
                return

            print(temp_file_path_1, '\n' + temp_file_path_2)

            # Удаляем временные файлы

            os.remove(f"{temp_file_path_1}")
            os.remove(f"{temp_file_path_2}")

            print('Everything is done, Master!')

        # Возвращаемся к панели ввода данных

        self.destroy()
        self.AppGUI.update()
        self.AppGUI.deiconify()
        self.AppGUI.focus()


# Класс части программы, отвечающий за выбор исходных файлов

class AppCore(tk.Tk):
    def __init__(self):
        super().__init__()

        # Задание интерфейса приложения

        self.title('English video creator - working panel v1.0.1 - by IgorVeshkin')
        self.update()
        self.screen_width, self.screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.update()

        self.window_width, self.window_height = 580, 265
        self.geometry("{}x{}+{}+{}".format(self.window_width, self.window_height,
                                           int(self.screen_width / 2 - self.window_width / 2),
                                           int(self.screen_height / 2 - self.window_height / 2)))
        self.resizable(False, False)

        self.iconbitmap('D:\Documents\Python_files\English_video_creator\English_Video_Creator_icon_1.ico')

        self.PathsFrame = tk.LabelFrame(self, text='Paths')
        self.PathsFrame.grid(row=0, column=0, columnspan=10, padx=5, pady=5, sticky="nesw")

        self.VideoPath_lbl = tk.Label(self.PathsFrame,
                                      text='Path to original video (.mp4): ')
        self.VideoPath_lbl.grid(row=0, column=0, padx=5, pady=5, sticky="nsw")

        self.VideoPath_entry = tk.Entry(self.PathsFrame, width=40)
        self.VideoPath_entry.grid(row=0, column=1, columnspan=7, padx=5, pady=5, sticky="nesw")

        # Следующее изменение будет применено, ко всем полям ввода данных
        # В поля запрещается вводить какие либо данные, можно только перемещаться по всей длине путя с помощью стрелочек
        # Это необходимо, чтобы предотвратить ошибки при прописание пути
        # Все пути до файлов будет выбираться посредством выбора файла из диалогового меню поиска файлов

        self.VideoPath_entry.bind('<Left>', self.move_in_entry)
        self.VideoPath_entry.bind('<Right>', self.move_in_entry)
        self.VideoPath_entry.bind('<Key>', lambda e: "break")

        self.VideoPath_btn = tk.Button(self.PathsFrame, text='Select Video', command=self.select_video)  # ,

        self.VideoPath_btn.grid(row=0, column=9, columnspan=2, padx=5, pady=5, sticky="nesw")

        self.EnglishSub_lbl = tk.Label(self.PathsFrame, text='Path to english subtitles (.ass): ')

        self.EnglishSub_lbl.grid(row=1, column=0, padx=5, pady=5, sticky="nsw")

        self.EnglishSub_entry = tk.Entry(self.PathsFrame, width=40)
        self.EnglishSub_entry.grid(row=1, column=1, columnspan=7, padx=5, pady=5, sticky="nesw")
        self.EnglishSub_entry.bind('<Left>', self.move_in_entry)
        self.EnglishSub_entry.bind('<Right>', self.move_in_entry)
        self.EnglishSub_entry.bind('<Key>', lambda e: "break")

        self.EnglishSub_btn = tk.Button(self.PathsFrame, text='Select English Subs',
                                        command=self.select_english_subs)

        self.EnglishSub_btn.grid(row=1, column=9, columnspan=2, padx=5, pady=5, sticky="nesw")

        self.RussianSub_lbl = tk.Label(self.PathsFrame, text='Path to russian subtitles (.ass): ')
        self.RussianSub_lbl.grid(row=2, column=0, padx=5, pady=5, sticky="nsw")

        self.RussianSub_entry = tk.Entry(self.PathsFrame, width=40)
        self.RussianSub_entry.grid(row=2, column=1, columnspan=7, padx=5, pady=5, sticky="nesw")
        self.RussianSub_entry.bind('<Left>', self.move_in_entry)
        self.RussianSub_entry.bind('<Right>', self.move_in_entry)
        self.RussianSub_entry.bind('<Key>', lambda e: "break")

        self.RussianSub_btn = tk.Button(self.PathsFrame, text='Select Russian Subs',
                                        command=self.select_russian_subs)

        self.RussianSub_btn.grid(row=2, column=9, columnspan=2, padx=5, pady=5, sticky="nesw")

        self.WatermarkPath_lbl = tk.Label(self.PathsFrame, text='Path to watermark (.png): ')

        self.WatermarkPath_lbl.grid(row=3, column=0, padx=5, pady=5, sticky="nsw")

        self.WatermarkPath_entry = tk.Entry(self.PathsFrame,
                                            width=40)
        self.WatermarkPath_entry.grid(row=3, column=1, columnspan=7, padx=5, pady=5, sticky="nesw")
        self.WatermarkPath_entry.bind('<Left>', self.move_in_entry)
        self.WatermarkPath_entry.bind('<Right>', self.move_in_entry)
        self.WatermarkPath_entry.bind('<Key>', lambda e: "break")

        self.WatermarkPath_btn = tk.Button(self.PathsFrame, text='Select watermark', command=self.select_watermark)  # ,

        self.WatermarkPath_btn.grid(row=3, column=9, columnspan=2, padx=5, pady=5, sticky="nesw")

        self.ChangedVideoPath_lbl = tk.Label(self.PathsFrame, text='Path to save new video (.mp4): ')

        self.ChangedVideoPath_lbl.grid(row=4, column=0, padx=5, pady=5, sticky="nsw")

        self.ChangedVideoPath_entry = tk.Entry(self.PathsFrame,
                                               width=40)
        self.ChangedVideoPath_entry.grid(row=4, column=1, columnspan=7, padx=5, pady=5, sticky="nesw")
        self.ChangedVideoPath_entry.bind('<Left>', self.move_in_entry)
        self.ChangedVideoPath_entry.bind('<Right>', self.move_in_entry)
        self.ChangedVideoPath_entry.bind('<Key>', lambda e: "break")

        self.ChangedVideoPath_btn = tk.Button(self.PathsFrame, text='Select New Path',
                                              command=self.save_video_as_btn)
        self.ChangedVideoPath_btn.grid(row=4, column=9, columnspan=2, padx=5, pady=5, sticky="nesw")

        self.TransparencyFactor_lbl = tk.Label(self.PathsFrame, text='Watermark transparency factor: ')

        self.TransparencyFactor_lbl.grid(row=5, column=0, padx=5, pady=5, sticky="ws")

        self.TransparencyFactor_scale = tk.Scale(self.PathsFrame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, digits=3,
                                                 resolution=0.01, length=240)  # ,

        self.TransparencyFactor_scale.grid(row=5, column=1, columnspan=9, padx=5, pady=5, sticky="ws")

        self.TransparencyFactor_scale.set(0.20)

        self.Execution_btn = tk.Button(self.PathsFrame, text="Execute", width=15, command=self.ffmpeg_execution)  # ,

        self.Execution_btn.grid(row=5, column=10, padx=5, pady=5, sticky="se")

        self.eng_sub_added, self.rus_sub_added, self.watermark_added = False, False, False

        self.mainloop()

    def move_in_entry(self, event):
        pass

    # Функция выбора исходного видео-файла

    def select_video(self):
        path_to_original_vid = filedialog.askopenfilename(filetypes=[(".mp4", ".mp4")])

        # Запись текста пути в соответствующее поле

        if path_to_original_vid:
            self.VideoPath_entry.delete(0, tk.END)
            self.VideoPath_entry.insert(0, f"{path_to_original_vid}")

    # Функция выбора английских субтитров

    def select_english_subs(self):
        path_to_english_sub = filedialog.askopenfilename(filetypes=[(".ass", ".ass")])

        if path_to_english_sub:
            self.EnglishSub_entry.delete(0, tk.END)
            self.EnglishSub_entry.insert(0, f"{path_to_english_sub}")

    # Функция выбора рускких субтитров

    def select_russian_subs(self):
        path_to_russian_sub = filedialog.askopenfilename(filetypes=[(".ass", ".ass")])

        if path_to_russian_sub:
            self.RussianSub_entry.delete(0, tk.END)
            self.RussianSub_entry.insert(0, f"{path_to_russian_sub}")

    # Функция выбора изображения водянного знака

    def select_watermark(self):
        path_to_watermark = filedialog.askopenfilename(filetypes=[(".png", ".png")])

        if path_to_watermark:
            self.WatermarkPath_entry.delete(0, tk.END)
            self.WatermarkPath_entry.insert(0, f"{path_to_watermark}")

    # Функция выбора пути сохранения конечного результата (видео-файла)

    def save_video_as_btn(self):

        path_to_saved_file = filedialog.asksaveasfilename(filetypes=[(".mp4", ".mp4")],
                                                          defaultextension=[(".mp4", ".mp4")])

        if path_to_saved_file:
            self.ChangedVideoPath_entry.delete(0, tk.END)
            self.ChangedVideoPath_entry.insert(0, f"{path_to_saved_file}")

    # Функция отлова логических несостыковок в выборе исходных данных
    # Например, не выбран исходный и/или конечный видео-файл
    # Или нет ни субтитров, ни водянного знака
    # Если выбраны не все компоненты (русские, английские субтитры, водянной знак), то программа спросить
    # пользователя о запуске программы преобразования, описанной выше
    # Если все файлы выбраны, то программа не выдаст сообщений

    def ffmpeg_execution(self):
        if not self.VideoPath_entry.get():
            messagebox.showwarning(title="Warning", message="You haven't specified path to original video!")
            return

        if not self.ChangedVideoPath_entry.get():
            messagebox.showwarning(title="Warning", message="You haven't specified path to modified video!")
            return

        print(self.EnglishSub_entry.get())

        if self.EnglishSub_entry.get():
            self.eng_sub_added = True

        else:
            self.eng_sub_added = False

        if self.RussianSub_entry.get():
            self.rus_sub_added = True

        else:
            self.rus_sub_added = False

        if self.WatermarkPath_entry.get():
            self.watermark_added = True

        else:
            self.watermark_added = False

        print(self.eng_sub_added, self.rus_sub_added, self.watermark_added)

        if not self.eng_sub_added and not self.rus_sub_added and not self.watermark_added:
            messagebox.showwarning(title="Warning", message="You have selected neither paths to russian/english "
                                                            "subtitles nor path to watermark!")
            return

        if not self.eng_sub_added and not self.rus_sub_added:
            continue_execution = messagebox.askyesno(title="Warning", message=
            "You have selected neither path to russian nor path to english subtitles!"
            "\nDo you want to continue?")

            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)

            return

        if not self.eng_sub_added and not self.watermark_added:
            continue_execution = messagebox.askyesno(title="Warning", message=
            "You have selected neither path to english subtitles nor path to watermark!"
            "\nDo you want to continue?")

            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)

            return

        if not self.rus_sub_added and not self.watermark_added:
            continue_execution = messagebox.askyesno(title="Warning", message=
            "You have selected neither path to russian subtitles nor path to watermark!"
            "\nDo you want to continue?")

            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)

            return

        if not self.eng_sub_added:
            continue_execution = messagebox.askyesno(title='Warning',
                                                     message="You haven't selected path to english subtitles!"
                                                             "\nDo you want to continue?")
            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)

            return

        if not self.rus_sub_added:
            continue_execution = messagebox.askyesno(title='Warning',
                                                     message="You haven't selected path to russian subtitles!"
                                                             "\nDo you want to continue?")
            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)
                return
            else:
                return

        if not self.watermark_added:
            continue_execution = messagebox.askyesno(title='Warning',
                                                     message="You haven't selected path to watermark!"
                                                             "\nDo you want to continue?")
            if continue_execution:
                execution_client = ExecutionGUI(main_gui=self)
                return
            else:
                return

        if Path(self.ChangedVideoPath_entry.get()).exists():

            os.remove(f"{self.ChangedVideoPath_entry.get()}")

        execution_client = ExecutionGUI(main_gui=self)

# Класс части программы отвечающей за скачивании ffmpeg.exe файла в случае, если такой
# не был обнаружен в папке с программой (py-файл или exe-файл)


class ffmpeg_downloading_gui(tk.Tk):
    def __init__(self):
        super().__init__()

        # Задание интерфейса программы

        self.title("ffmpeg downloading is in the process")
        self.update()
        self.screen_width, self.screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        self.update()

        self.window_width, self.window_height = 400, 100
        self.geometry("{}x{}+{}+{}".format(self.window_width, self.window_height,
                                           int(self.screen_width / 2 - self.window_width / 2),
                                           int(self.screen_height / 2 - self.window_height / 2)))
        self.resizable(False, False)

        self.iconbitmap('D:\Documents\Python_files\English_video_creator\English_Video_Creator_icon_1.ico')

        self.progressbar_width, self.progressbar_height = 280, 20
        self.download_statues = ttk.Progressbar(self,
                                                orient='horizontal',
                                                mode='determinate',
                                                length=100,
                                                value=0,
                                                maximum=100
                                                )

        self.download_statues.place(x=self.window_width / 2 - self.progressbar_width / 2,
                                    y=20,
                                    width=self.progressbar_width,
                                    height=self.progressbar_height)

        self.cmd_progress_bar = []

        self.Info_label = tk.Label(self, text="Происходит скачивание ffmpeg.exe")
        self.Info_label.place(x=self.window_width / 2 - 125,
                              y=40,
                              width=250,
                              height=20)

        self.Wait_label = tk.Label(self, text="Подождите")
        self.Wait_label.place(x=self.window_width / 2 - 125,
                              y=60,
                              width=250,
                              height=20)

        self.total_size_in_bytes = 0
        self.data_info_label = tk.Label(self,
                                        text="Скачано: {downloaded}/{full:.1f} MB".format(downloaded=0,
                                                                                          full=100827136 / 1024000))
        self.data_info_label.place(x=self.window_width / 2 - 125,
                                   y=80,
                                   width=250,
                                   height=20)

        self.current_path = os.path.abspath(os.path.dirname(sys.argv[0])) + '\\'

        # Задание ссылки сервиса и ссылки скачивания ffmpeg.exe файла с yandex disk

        self.base_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
        self.ffmpeg_url = 'https://disk.yandex.ru/d/22G8EEPcb2A0vA'

        self.download_thread_active = True
        self.wait_label_action()

        # Запускаем новый поток, чтобы интерфейс продолжал функционировать (не застыл) при выполнение скачивания

        self.download_thread = threading.Thread(target=self.download_ffmpeg, args=())
        self.download_thread.daemon = True
        self.download_thread.start()

        # Выполняем определенную функцию при закрытие окна интерфейса приложения

        self.protocol("WM_DELETE_WINDOW", self.close_download_gui)

        self.mainloop()

    def download_ffmpeg(self):
        global total_size, cur_size

        try:
            # Получаем загрузочную ссылку, с помощью парссинга
            final_url = self.base_url + urlencode(dict(public_key=self.ffmpeg_url))
            response = requests.get(final_url)
            download_url = response.json()['href']

            # Загружаем файл и сохраняем его

            download_response = requests.get(download_url, stream=True)

            self.update()
            self.deiconify()

            # Подгружаем максимальное объем скачиваемого файла

            self.total_size_in_bytes = int(download_response.headers.get('content-length', 0))

            # Скачивание происходим по блогам размером 1024 байта

            block_size = 1024

            # Задаем максимальное значение для progressbar

            self.download_statues.config(maximum=int(self.total_size_in_bytes))

            print(self.total_size_in_bytes, self.download_statues['maximum'])
            self.download_statues['value'] = 0

            total_size = self.total_size_in_bytes

            total_MB = self.total_size_in_bytes / 1024000

            # Создаем файл ffmpeg.exe в папке с программой и начинаем скачивание

            if self.download_thread_active:
                with open(self.current_path + 'ffmpeg.exe', 'wb') as f:
                    for data in download_response.iter_content(block_size):

                        # Корректируем значение progressbar в режиме реального времени

                        self.download_statues['value'] += int(len(data))
                        cur_downloaded_MB = self.download_statues['value'] / 1024000

                        # Корректируем значение строки, сигнализурующую скачанный объем, в режиме реального времени
                        self.data_info_label.config(text="Скачано: {downloaded:.1f}/{full:.1f} MB".format(
                            downloaded=cur_downloaded_MB,
                            full=total_MB))

                        cur_size = self.download_statues['value']

                        # Записываем файл

                        f.write(data)

                        if not self.download_thread_active:
                            break

                    else:
                        print('here =', self.download_statues['value'], self.total_size_in_bytes)

                        total_size, cur_size = self.total_size_in_bytes, self.download_statues['value']

                        self.quit()

            self.quit()

        # Если отсутствует интернет-соединение, то выводим ошибку и выходим из программы

        except requests.exceptions.ConnectionError as er:
            self.withdraw()
            messagebox.showerror(title='Ошибка подключения', message='Отсутствует интернет-подключение!'
                                                                     ' Восстановите интернет-подключение для '
                                                                     'скачивания ffmpeg.exe')
            self.quit()
            return

    # Функция закрытия приложения

    def close_download_gui(self):

        # В случае если объем скаченного файла соответсует объему заданному в начале программы, то

        if int(self.download_statues['value']) == int(self.total_size_in_bytes):
            print('here =', int(self.download_statues['value']), int(self.total_size_in_bytes))
            self.download_thread_active = False

            # Выходим из приложения

            self.destroy()
        else:

            # Выводим сообщение об отмене скачивания и завершаем программу

            self.download_thread_active = False
            self.quit()
            messagebox.showwarning(title='Отмена скачивания',
                                   message='Скачивание файла ffmpeg.exe было отменено!')

            os.remove(self.current_path + 'ffmpeg.exe')

    def progressbar_action(self, direction='forward'):

        if direction == 'forward':
            self.download_statues['value'] += 10
        elif direction == 'backward':
            self.download_statues['value'] -= 10

        if self.download_statues['value'] <= 0:
            direction = 'forward'
        elif self.download_statues['value'] >= 100:
            direction = 'backward'

        self.after(100, lambda: self.progressbar_action(direction))

    # Анимация текста

    def wait_label_action(self, counter=0):
        if self.download_thread_active:
            self.Wait_label['text'] += '.'
            counter += 1

            if counter == 6:
                self.Wait_label['text'] = self.Wait_label['text'][:-6]
                counter = 0

            self.after(400, lambda: self.wait_label_action(counter))


# Главная функция


def main():
    # Если в папке где лежит файл приложения нет файла ffmpeg.exe
    if not os.path.isfile(os.path.abspath(os.path.dirname(sys.argv[0])) + '\\' + 'ffmpeg.exe'):

        # Запускаем клиент-скачивания ffmpeg.exe
        download_client = ffmpeg_downloading_gui()

        # Если размеры скаченого файла совпадают, с размером прописанным в приложении, то
        if cur_size == total_size:
            # Поток отвечающий за параллельную работу скачивания, отключается
            download_client.download_thread_active = False

            # Клиент-скачивания ffmpeg.exe удаляется
            download_client.destroy()

            # Запускается окно-панель обработки видео
            main_client = AppCore()

        print('ffmpeg is necessary')
    else:
        main_client = AppCore()


# Запуск функции main


if __name__ == '__main__':
    main()
