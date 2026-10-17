"""Semantic light/dark tokens shared by desktop and workbook views."""
import customtkinter as ctk

COLORS = {
    "canvas": ("#F2F5F9", "#0B101B"),
    "sidebar": ("#FFFFFF", "#101725"),
    "surface": ("#FFFFFF", "#151E2E"),
    "inset": ("#EDF1F7", "#0E1624"),
    "hover": ("#E4EAF3", "#243149"),
    "border": ("#C6D0DF", "#455571"),
    "text": ("#162237", "#F0F4FC"),
    "muted": ("#53627A", "#A7B6CC"),
    "accent": ("#B92F43", "#B92F43"),
    "accent_hover": ("#9F2336", "#9F2336"),
    "accent_soft": ("#FCE8ED", "#341D2D"),
    "accent_text": ("#B0253B", "#FF9AA9"),
    "success": ("#16745E", "#6DD9B4"),
    "warning": ("#8C590E", "#F5C879"),
    "danger": ("#BA263E", "#FF98AA"),
    "blue": ("#285AB0", "#8DB8FF"),
    "selection": ("#DBE8FF", "#2B4166"),
}


def color(name):
    return COLORS[name]


def resolved(name):
    return color(name)[ctk.get_appearance_mode() == "Dark"]


def label(parent, text, size=13, bold=False, muted=False, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family="Segoe UI", size=size,
                       weight="bold" if bold else "normal"),
                       text_color=color("muted" if muted else "text"), **kwargs)


def button(parent, text, command, primary=False, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command, height=40, corner_radius=10,
                        fg_color=color("accent" if primary else "inset"),
                        hover_color=color("accent_hover" if primary else "hover"),
                        text_color="#FFFFFF" if primary else color("text"),
                        text_color_disabled=color("muted"),
                        border_width=0 if primary else 1,
                        border_color=color("border"), font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                        **kwargs)


def entry(parent, **kwargs):
    return ctk.CTkEntry(parent, height=40, corner_radius=9, fg_color=color("inset"),
                       border_color=color("border"), text_color=color("text"),
                       font=ctk.CTkFont(family="Segoe UI", size=13), **kwargs)
