from abc import ABC
from typing import Optional

import flet as ft

from pathlib import Path
from pydantic import BaseModel, ValidationError
import tomllib

import subprocess
from threading import Thread
from multiprocessing import Event

import re

from mgl77.fetch import fetch
from mgl77.game_data import NavigationColumn, AllGameData
from mgl77.time_keeper import time_keep

import time
import win32gui, win32process, win32con

import pyautogui as pag

import sys
import os
import keyboard

if getattr(sys, "frozen", False):
    # exeとして実行されている場合、3つ上のフォルダを基準にする
    os.chdir(Path(sys.executable).parent.parent.parent)

game_process: Optional[subprocess.Popen] = None
time_keeper_thread: Optional[Thread] = None
kill_window_event: Event = Event()
end_thread_event: Event = Event()


# プロセスIDからウィンドウハンドルを取得
def get_hwnds_from_pid(pid):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds


def main(page: ft.Page):
    page.title = "Mini game launcher"

    img_controller: Optional[ft.Container] = None
    img_part: Optional[ft.Container] = None

    def route_change(e):
        nonlocal img_controller, img_part
        global time_keeper_thread, kill_window_event, end_thread_event

        page.views.clear()
        page.views.append(
            ft.View(
                "/",
                [
                    ft.Text(
                        "AGC展ミニゲーム集", size=100, text_align=ft.TextAlign.CENTER
                    ),
                    ft.ElevatedButton(
                        content=ft.Text("はじめる", size=36),
                        width=200,
                        height=80,
                        on_click=lambda _: page.go("/games/0"),
                    ),
                ],
                spacing=80,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        if page.route == "/":
            # fetch()

            if time_keeper_thread is not None:
                end_thread_event.set()
                time_keeper_thread.join()

                kill_window_event = Event()
                end_thread_event = Event()

            if game_process is not None:
                game_process.terminate()
                game_process.wait()

        if m := re.match("/games/(.*)", page.route):
            if time_keeper_thread is None:

                def kill():
                    page.window_destroy()
                    if game_process is not None:
                        game_process.terminate()
                        game_process.wait()

                time_keeper_thread = Thread(
                    target=time_keep, args=(kill_window_event, end_thread_event, kill)
                )
                time_keeper_thread.start()

            num = int(m.group(1))

            nav = NavigationColumn(AllGameData())

            game_data = nav.gallery.control_groups[num]

            for it in nav.gallery.control_groups:
                if it.index == num:
                    nav.gallery.selected_control_group = it
                    break

            img_w = page.width / 10 * 7
            img_h = page.height - 200

            if nav.gallery.selected_control_group.screen_shot is not None:
                img_controller = ft.Image(
                    src=str(nav.gallery.selected_control_group.screen_shot.absolute()),
                    width=img_w,
                    height=img_h,
                    fit=ft.ImageFit.COVER,
                    border_radius=ft.border_radius.all(10),
                )
            else:
                img_controller = ft.Container(
                    bgcolor=ft.colors.GREY,
                    width=img_w,
                    height=img_h,
                    border_radius=ft.border_radius.all(10),
                )
            play_button = ft.Container(
                ft.Text("あそぶ", size=40),
                bgcolor=ft.colors.GREEN,
                ink_color=ft.colors.GREEN,
                on_click=lambda e: game_on_click(e),
                padding=ft.Padding(20, 10, 20, 10),
                border_radius=ft.border_radius.all(10),
                visible=True,
            )
            stop_button = ft.Container(
                ft.Text("とめる", size=40),
                bgcolor=ft.colors.RED,
                ink_color=ft.colors.RED,
                on_click=lambda _: stop_game(),
                padding=ft.Padding(20, 10, 20, 10),
                border_radius=ft.border_radius.all(10),
                visible=False,
            )

            def stop_game():
                global game_process
                if game_process is not None and game_process.poll() is None:
                    game_process.terminate()
                    game_process.wait()
                    game_process = None
                play_button.visible = True
                stop_button.visible = False
                page.update()

            def game_on_click(e):
                global game_process

                if game_process is not None and game_process.poll() is not None:
                    game_process = None

                if game_process is not None:

                    def close_dlg(e):
                        dlg.open = False
                        page.update()

                    dlg = ft.AlertDialog(
                        title=ft.Text("エラー"),
                        content=ft.Text(
                            "すでにゲームが起動しています。そちらを終了してから始めてください"
                        ),
                        actions=[
                            ft.TextButton("OK", on_click=close_dlg),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                        on_dismiss=lambda e: print("dialog dismissed!"),
                    )

                    page.dialog = dlg
                    dlg.open = True
                    page.update()

                    return

                game_process = subprocess.Popen([str(game_data.game_exe.absolute())])

                def show_stop_button():
                    time.sleep(1.0)
                    play_button.visible = False
                    stop_button.visible = True
                    page.update()

                Thread(target=show_stop_button).start()

                def watch_game():
                    if game_process is not None:
                        game_process.wait()  # ゲームが終わるまで待つ
                    stop_game()

                Thread(target=watch_game).start()

                page.update()

                def get_hwnds():
                    time.sleep(0.5)
                    if game_process is None:
                        return []
                    hwnds = get_hwnds_from_pid(game_process.pid)
                    return hwnds

                hwnds = get_hwnds()
                while len(hwnds) == 0:
                    if game_process is None:
                        return
                    hwnds = get_hwnds()
                win32gui.SetWindowPos(
                    hwnds[0],
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
                l, t, _, _ = win32gui.GetWindowRect(hwnds[0])
                pag.moveTo(l + 60, t + 10)
                pag.click()

            img_part = ft.Container(
                ft.Column(
                    [
                        ft.Container(
                            ft.Row(
                                [
                                    ft.Text(game_data.title, size=45),
                                    ft.Text(
                                        game_data.description,
                                        size=20,
                                        expand=True,
                                        overflow=ft.TextOverflow.CLIP,
                                    ),
                                    play_button,
                                    stop_button,
                                ],
                            ),
                            border=ft.border.all(2),
                            border_radius=ft.border_radius.all(10),
                            padding=ft.Padding(20, 10, 10, 10),
                        ),
                        img_controller,
                    ],
                    width=img_w,
                ),
            )

            def on_keyboard(e: ft.KeyboardEvent):
                nav_items = nav.get_navigation_items()

                if e.key == "Arrow Down":
                    nav.select((num + 1) % len(nav_items))
                    nav.update_selected_item()
                elif e.key == "Arrow Up":
                    nav.select((num - 1) % len(nav_items))
                    nav.update_selected_item()
                elif e.key == "Enter":
                    game_on_click(e)

            last_delete_time = 0

            def on_delete():
                nonlocal last_delete_time
                now = time.time()
                if now - last_delete_time < 1.0:  # 1秒以内の連続入力を無視
                    return
                last_delete_time = now

                if game_process is None or game_process.poll() is not None:
                    page.go("/")
                else:
                    stop_game()

            keyboard.unhook_all()
            keyboard.on_release_key("delete", lambda _: on_delete())
            page.on_keyboard_event = on_keyboard

            page.views.append(
                ft.View(
                    "/games",
                    [
                        ft.AppBar(
                            title=ft.Text("ミニゲーム一覧"),
                            leading=ft.Container(
                                ft.ElevatedButton(
                                    "やめる", on_click=lambda _: page.go("/")
                                ),
                                padding=5,
                            ),
                            leading_width=120,
                            bgcolor=ft.colors.SURFACE_VARIANT,
                        ),
                        ft.Row(
                            [
                                nav,
                                img_part,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ],
                )
            )

        page.update()

    def page_resized(e):
        nonlocal img_controller, img_part
        if img_controller is not None:
            img_controller.width = page.width / 10 * 7
            img_controller.height = page.height - 200
            img_part.width = img_controller.width

        page.update()

    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_resize = page_resized
    page.on_view_pop = view_pop

    page.go(page.route)

    def window_event_handler(e):
        if e.data == "close":
            keyboard.unhook_all()
            page.window_destroy()
            if game_process is not None:
                game_process.terminate()
                game_process.wait()
                end_thread_event.set()

    page.window_prevent_close = True
    page.on_window_event = window_event_handler


if __name__ == "__main__":
    try:
        ft.app(target=main, view=ft.AppView.FLET_APP)
    finally:
        if game_process is not None:
            game_process.terminate()
            game_process.wait()
