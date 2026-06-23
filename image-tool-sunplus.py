import os
import io
import lzma
import zlib
import subprocess
from dataclasses import dataclass

def install():
    try:
        import customtkinter
        from PIL import Image, ImageTk
    except:
        subprocess.check_call(["pip", "install", "customtkinter", "pillow"])

install()

import customtkinter as ctk
from PIL import Image, ImageTk, ImageFile
import tkinter as tk
from tkinter import filedialog, messagebox

ImageFile.LOAD_TRUNCATED_IMAGES = True

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

@dataclass
class Img:
    index: int
    offset: int
    block: int
    width: int
    height: int
    data: bytes
    is_little: bool

class SunplusEngine:
    def __init__(self, data, log):
        self.data = bytearray(data)
        self.log = log
        self.images = []

    def extract(self):
        self.images.clear()
        blocks = []
        pos = 0
        
        while True:
            p = self.data.find(b"\x5d\x00\x00", pos)
            if p == -1:
                break
            blocks.append((p, False))
            pos = p + 3

        pos = 0
        while True:
            p = self.data.find(b"\x00\x00\x5d", pos)
            if p == -1:
                break
            blocks.append((p, True))
            pos = p + 3

        self.log(f"Total LZMA entry vectors scanned: {len(blocks)}")
        idx = 0
        
        for b, is_little in blocks:
            try:
                payload = self.data[b:]
                if is_little:
                    payload = bytearray(payload)
                    for i in range(0, len(payload) - 3, 4):
                        payload[i], payload[i+3] = payload[i+3], payload[i]
                        payload[i+1], payload[i+2] = payload[i+2], payload[i+1]
                
                dec = lzma.decompress(bytes(payload))
                self._scan(dec, b, idx, is_little)
                idx += 1
            except:
                continue

        self.log(f"Validated and parsed images: {len(self.images)}")
        return self.images

    def _scan(self, data, offset, block, is_little):
        pos = 0
        while True:
            s = data.find(b"\xff\xd8\xff", pos)
            if s == -1:
                break
            e = data.find(b"\xff\xd9", s)
            if e == -1:
                break
            raw = data[s:e+2]
            try:
                img = Image.open(io.BytesIO(raw))
                img.load()
                self.images.append(Img(
                    index=len(self.images),
                    offset=offset + s,
                    block=block,
                    width=img.width,
                    height=img.height,
                    data=raw,
                    is_little=is_little
                ))
            except:
                pass
            pos = e + 2

    def replace(self, idx, raw_new_data):
        target = self.images[idx]
        final = None
        if len(raw_new_data) <= len(target.data):
            final = raw_new_data
        else:
            final = raw_new_data[:len(target.data)]
        final = final.ljust(len(target.data), b"\x00")
        
        dec = bytearray(lzma.decompress(self.data[target.offset:]))
        pos = target.offset % len(dec)
        dec[pos:pos+len(target.data)] = final
        
        recom = lzma.compress(bytes(dec), format=lzma.FORMAT_ALONE)
        self.data[target.offset:target.offset+len(recom)] = recom
        self.log(f"Synchronized structural frame target: {idx}")
        return True

    def fix_crc(self):
        try:
            crc = zlib.crc32(self.data[:-4]) & 0xFFFFFFFF
            self.data[-4:] = crc.to_bytes(4, "little")
            self.log(f"CRC checksum calculated: {hex(crc)}")
        except Exception as e:
            self.log(f"CRC block verify bypassed: {str(e)}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DRAGON_NOIR_SUNPLUS-IMAGE CHANG_V3")
        self.geometry("1450x920")
        self.minsize(1280, 850)
        
        self.engine = None
        self.selected = None
        self.tk_orig = None
        self.tk_new = None
        self.loaded_new_img = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self, 
            text="DRAGON_NOIR_SUNPLUS-IMAGE CHANG", 
            font=("Consolas", 32, "bold"),
            text_color="#00FFCC"
        )
        self.title_label.grid(row=0, column=0, padx=30, pady=(25, 10), sticky="w")

        self.top_frame = ctk.CTkFrame(self, corner_radius=22, fg_color="#141419", border_width=2, border_color="#00FFCC")
        self.top_frame.grid(row=1, column=0, padx=30, pady=15, sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)

        self.btn_browse = ctk.CTkButton(
            self.top_frame, text="BROWSE FIRMWARE", font=("Segoe UI", 14, "bold"),
            fg_color="#1F538D", hover_color="#2B74C5", height=55, width=220, corner_radius=12, command=self.open
        )
        self.btn_browse.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.entry_path = ctk.CTkEntry(
            self.top_frame, font=("Segoe UI", 13), fg_color="#0A0A0C",
            border_color="#2A2A35", height=55, corner_radius=12, text_color="#E0E0E0"
        )
        self.entry_path.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

        self.btn_save_fw = ctk.CTkButton(
            self.top_frame, text="SAVE FIRMWARE", font=("Segoe UI", 14, "bold"),
            fg_color="#2EB85C", hover_color="#229949", height=55, width=200, corner_radius=12, state="disabled", command=self.save_file
        )
        self.btn_save_fw.grid(row=0, column=2, padx=20, pady=20, sticky="e")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=2)

        self.left_panel = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="#141419", border_width=2, border_color="#2A2A35")
        self.left_panel.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.lbl_list = ctk.CTkLabel(self.left_panel, text="INDEX ALLOCATION BLOCKS", font=("Segoe UI", 16, "bold"), text_color="#FFB300")
        self.lbl_list.grid(row=0, column=0, padx=25, pady=20, sticky="w")

        self.listbox = tk.Listbox(
            self.left_panel, bg="#0A0A0C", fg="#E0E0E0", selectbackground="#00FFCC",
            selectforeground="#0A0A0C", borderwidth=0, highlightthickness=1, highlightbackground="#2A2A35",
            font=("Consolas", 13, "bold"), activestyle="none"
        )
        self.listbox.grid(row=1, column=0, padx=25, pady=(0, 25), sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.select)

        self.right_panel = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="#141419", border_width=2, border_color="#2A2A35")
        self.right_panel.grid(row=0, column=1, padx=(20, 0), sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(1, weight=1)

        self.control_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.control_bar.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")

        self.btn_extract_orig = ctk.CTkButton(
            self.control_bar, text="EXTRACT ORIGINAL IMAGE", font=("Segoe UI", 14, "bold"),
            fg_color="#00A8CC", hover_color="#00C4ED", height=60, corner_radius=12, state="disabled", command=self.extract_original
        )
        self.btn_extract_orig.pack(side="left", padx=10, expand=True, fill="x")

        self.btn_load_new = ctk.CTkButton(
            self.control_bar, text="OPEN REPLACEMENT TARGET", font=("Segoe UI", 14, "bold"),
            fg_color="#8A2BE2", hover_color="#9A42F4", height=60, corner_radius=12, state="disabled", command=self.load_new_image
        )
        self.btn_load_new.pack(side="left", padx=10, expand=True, fill="x")

        self.btn_merge = ctk.CTkButton(
            self.control_bar, text="MERGE IMAGE BUFFER", font=("Segoe UI", 14, "bold"),
            fg_color="#E056FD", hover_color="#BE2EDD", height=60, corner_radius=12, state="disabled", command=self.merge_image
        )
        self.btn_merge.pack(side="right", padx=10, expand=True, fill="x")

        self.orig_container = ctk.CTkFrame(self.right_panel, corner_radius=16, fg_color="#0A0A0C", border_width=1, border_color="#2A2A35")
        self.orig_container.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.orig_container.grid_rowconfigure(1, weight=1)
        self.orig_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.orig_container, text="ORIGINAL DISPLAY MATRIX", font=("Segoe UI", 13, "bold"), text_color="#777788").grid(row=0, column=0, pady=15)
        self.lbl_orig_preview = ctk.CTkLabel(self.orig_container, text="AWAITING SYSTEM SELECTION", font=("Segoe UI", 13))
        self.lbl_orig_preview.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        self.new_container = ctk.CTkFrame(self.right_panel, corner_radius=16, fg_color="#0A0A0C", border_width=1, border_color="#2A2A35")
        self.new_container.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.new_container.grid_rowconfigure(1, weight=1)
        self.new_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.new_container, text="REPLACEMENT COMPILER STAGING", font=("Segoe UI", 13, "bold"), text_color="#777788").grid(row=0, column=0, pady=15)
        self.lbl_new_preview = ctk.CTkLabel(self.new_container, text="AWAITING REPLACEMENT SOURCE", font=("Segoe UI", 13))
        self.lbl_new_preview.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        self.log_frame = ctk.CTkFrame(self, corner_radius=20, fg_color="#141419", border_width=2, border_color="#2A2A35")
        self.log_frame.grid(row=3, column=0, padx=30, pady=(15, 30), sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.logbox = tk.Text(
            self.log_frame, height=5, bg="#0A0A0C", fg="#00FFCC",
            borderwidth=0, highlightthickness=1, highlightbackground="#2A2A35",
            font=("Consolas", 12), insertbackground="white"
        )
        self.logbox.grid(row=0, column=0, padx=25, pady=20, sticky="ew")

    def log(self, m):
        self.logbox.insert("end", f"[SYSTEM] >> {m}\n")
        self.logbox.see("end")

    def open(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, path)
        
        with open(path, "rb") as f:
            data = f.read()

        self.engine = SunplusEngine(data, self.log)
        imgs = self.engine.extract()

        self.listbox.delete(0, "end")
        for i, im in enumerate(imgs):
            mode_str = "L-Endian" if im.is_little else "B-Endian"
            self.listbox.insert("end", f" [{mode_str}] ADDR: {i:03d} | Size: {im.width}x{im.height}")

        self.btn_save_fw.configure(state="normal")
        self.selected = None
        self.btn_extract_orig.configure(state="disabled")
        self.btn_load_new.configure(state="disabled")
        self.btn_merge.configure(state="disabled")

    def select(self, e):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.selected = sel[0]
        self.btn_extract_orig.configure(state="normal")
        self.btn_load_new.configure(state="normal")
        
        raw_data = self.engine.images[self.selected].data
        img = Image.open(io.BytesIO(raw_data))
        
        img.thumbnail((500, 380))
        self.tk_orig = ImageTk.PhotoImage(img)
        self.lbl_orig_preview.configure(image=self.tk_orig, text="")
        
        if self.loaded_new_img:
            self.process_new_image_preview()

    def extract_original(self):
        if self.selected is None:
            return
        target = self.engine.images[self.selected]
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG Target", "*.jpg")],
            initialfile=f"dump_{self.selected}_{target.width}x{target.height}.jpg"
        )
        if not path:
            return
        try:
            img = Image.open(io.BytesIO(target.data))
            img.save(path, "JPEG", quality=100)
            self.log(f"Extracted file saved successfully: {path}")
            messagebox.showinfo("Success", "Original file saved safely to disk.")
        except Exception as ex:
            self.log(f"Extraction failed: {str(ex)}")

    def load_new_image(self):
        if self.selected is None:
            return
        path = filedialog.askopenfilename(filetypes=[("Valid Graphics", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        try:
            self.loaded_new_img = Image.open(path)
            self.process_new_image_preview()
        except Exception as ex:
            self.log(f"Failed loading file: {str(ex)}")

    def process_new_image_preview(self):
        if not self.loaded_new_img or self.selected is None:
            return
        target = self.engine.images[self.selected]
        
        processed = self.loaded_new_img.convert("RGB")
        processed = processed.resize((target.width, target.height), Image.Resampling.LANCZOS)
        
        display_img = processed.copy()
        display_img.thumbnail((500, 380))
        self.tk_new = ImageTk.PhotoImage(display_img)
        self.lbl_new_preview.configure(image=self.tk_new, text="")
        
        self.btn_merge.configure(state="normal")

    def merge_image(self):
        if self.selected is None or not self.loaded_new_img:
            return
        target = self.engine.images[self.selected]
        processed = self.loaded_new_img.convert("RGB")
        processed = processed.resize((target.width, target.height), Image.Resampling.LANCZOS)
        
        final_data = None
        for q in range(95, 5, -5):
            buf = io.BytesIO()
            processed.save(buf, format="JPEG", quality=q, optimize=True)
            data = buf.getvalue()
            if len(data) <= len(target.data):
                final_data = data
                break

        if not final_data:
            buf = io.BytesIO()
            processed.save(buf, format="JPEG", quality=10, optimize=True)
            final_data = buf.getvalue()[:len(target.data)]

        if self.engine.replace(self.selected, final_data):
            messagebox.showinfo("Merged", "Image safely injected and compiled back inside original memory container block.")

    def save_file(self):
        if not self.engine:
            return
        self.engine.fix_crc()
        path = filedialog.asksaveasfilename(defaultextension=".bin", filetypes=[("ROM Binaries", "*.bin"), ("All Files", "*.*")])
        if not path:
            return
        with open(path, "wb") as f:
            f.write(self.engine.data)
        self.log(f"Firmware output updated cleanly: {path}")
        messagebox.showinfo("Compiled", "The modified firmware package has been compiled successfully.")

if __name__ == "__main__":
    App().mainloop()