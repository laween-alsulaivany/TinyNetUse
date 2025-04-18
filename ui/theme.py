import customtkinter as ctk


def apply_theme(theme_name):
    ctk.set_appearance_mode(theme_name)  # "light" or "dark"
    ctk.set_default_color_theme("blue")  # or your custom .json theme
