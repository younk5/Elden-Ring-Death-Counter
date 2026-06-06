import tkinter as tk
from tkinter import font as tkfont, colorchooser
import threading, datetime, os, sys, time
import numpy as np

try:
    import cv2, mss
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "mss", "numpy"])
    import cv2, mss

LOWER = np.array([165, 60, 30], dtype=np.uint8)
UPPER = np.array([180, 255, 160], dtype=np.uint8)

LET_H_MIN, LET_H_MAX = 55, 105
LET_W_MIN, LET_W_MAX = 35, 100

MIN_LETRAS    = 8
MAX_Y_SPREAD  = 20
MIN_SPAN_FRAC = 0.25
MAX_GAP_LETRAS = 80

ROI = dict(y1=0.42, y2=0.75, x1=0.12, x2=0.88)

COOLDOWN    = 5.0
OUTPUT_FILE = "voce_morreu.txt"

C = dict(
    bg="#111111", painel="#0a0a0a",
    vermelho="#8b1a1a", vermelho2="#c0392b",
    ouro="#c9a227", texto="#d4c5a0",
    cinza="#555555", verde="#27ae60",
    btn="#1e1e1e", btn_h="#2a2a2a",
)

DEFAULT_OVERLAY_COLOR = "#c9a227"
DEFAULT_OVERLAY_SIZE  = 44


def _ler_count():
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            v = f.read().strip()
            return int(v) if v.isdigit() else 0
    except Exception:
        return 0

def _salvar(n):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(str(n))


class Detector(threading.Thread):
    def __init__(self, on_morte):
        super().__init__(daemon=True)
        self.on_morte = on_morte
        self._ativo   = True
        self._ultimo  = 0.0

    def parar(self):
        self._ativo = False

    def run(self):
        BASE_W, BASE_H = 1920, 1080
        with mss.mss() as sct:
            mon = sct.monitors[1]
            while self._ativo:
                try:
                    raw   = np.array(sct.grab(mon))
                    frame = cv2.resize(
                        cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR),
                        (BASE_W, BASE_H), interpolation=cv2.INTER_AREA
                    )
                    if self._verificar(frame, BASE_W, BASE_H):
                        agora = time.time()
                        if agora - self._ultimo >= COOLDOWN:
                            self._ultimo = agora
                            self.on_morte(frame)
                except Exception:
                    pass
                time.sleep(0.35)

    def _verificar(self, frame, W, H):
        y1 = int(H * ROI["y1"]); y2 = int(H * ROI["y2"])
        x1 = int(W * ROI["x1"]); x2 = int(W * ROI["x2"])
        roi = frame[y1:y2, x1:x2]

        hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LOWER, UPPER)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(cnts) < MIN_LETRAS:
            return False

        letras = []
        for cnt in cnts:
            x, y, w, h = cv2.boundingRect(cnt)
            if (LET_H_MIN <= h <= LET_H_MAX and
                    LET_W_MIN <= w <= LET_W_MAX and
                    cv2.contourArea(cnt) > 200):
                letras.append((x, y, w, h))

        if len(letras) < MIN_LETRAS:
            return False

        ys = [y for _, y, _, _ in letras]
        if max(ys) - min(ys) > MAX_Y_SPREAD:
            return False

        letras_x = sorted(letras, key=lambda l: l[0])
        span = (letras_x[-1][0] + letras_x[-1][2]) - letras_x[0][0]
        if span < W * MIN_SPAN_FRAC:
            return False

        for i in range(len(letras_x) - 1):
            gap = letras_x[i+1][0] - (letras_x[i][0] + letras_x[i][2])
            if gap > MAX_GAP_LETRAS:
                return False

        return True


class Overlay(tk.Toplevel):
    def __init__(self, master, var_mortes, cor=DEFAULT_OVERLAY_COLOR, tamanho=DEFAULT_OVERLAY_SIZE):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.85)
        self.configure(bg="black")
        self.wm_attributes("-transparentcolor", "black")

        self._drag_x = self._drag_y = 0
        self._cor    = cor
        self._tam    = tamanho
        self.geometry("160x80+20+20")

        self._fonte = tkfont.Font(family="Georgia", size=tamanho, weight="bold")
        self._lbl   = tk.Label(self, textvariable=var_mortes,
                               font=self._fonte, fg=cor, bg="black")
        self._lbl.pack(expand=True)

        self._lbl.bind("<ButtonPress-1>", self._drag_start)
        self._lbl.bind("<B1-Motion>",     self._drag_move)
        self.bind("<ButtonPress-3>",      lambda e: self.withdraw())

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def set_cor(self, cor):
        self._cor = cor
        self._lbl.config(fg=cor)

    def set_tamanho(self, tam):
        self._tam = tam
        self._fonte.config(size=tam)

    def set_posicao(self, x, y):
        self.geometry(f"+{x}+{y}")

    def get_posicao(self):
        return self.winfo_x(), self.winfo_y()


class JanelaOverlay(tk.Toplevel):
    def __init__(self, master, overlay):
        super().__init__(master)
        self.title("Configurar Overlay")
        self.geometry("300x260")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.attributes("-topmost", True)
        self._overlay = overlay

        fonte_titulo = tkfont.Font(family="Georgia", size=10, weight="bold")
        fonte_label  = tkfont.Font(family="Georgia", size=9)
        fonte_small  = tkfont.Font(family="Georgia", size=8)

        tk.Label(self, text="OVERLAY", bg=C["bg"], fg=C["ouro"],
                 font=fonte_titulo).pack(pady=(14, 2))
        tk.Frame(self, bg=C["ouro"], height=1, width=240).pack(pady=4)

        # Cor
        fr_cor = tk.Frame(self, bg=C["bg"]); fr_cor.pack(pady=6, padx=16, fill="x")
        tk.Label(fr_cor, text="Cor do número", bg=C["bg"], fg=C["texto"],
                 font=fonte_label).pack(side="left")
        self._preview = tk.Label(fr_cor, bg=overlay._cor, width=4, relief="flat")
        self._preview.pack(side="right", padx=4)
        tk.Button(fr_cor, text="Escolher", command=self._escolher_cor,
                  bg=C["btn"], fg=C["texto"], relief="flat",
                  activebackground=C["btn_h"], activeforeground=C["texto"],
                  font=fonte_small, cursor="hand2", bd=0,
                  highlightthickness=0, padx=8, pady=4).pack(side="right")

        # Tamanho
        fr_tam = tk.Frame(self, bg=C["bg"]); fr_tam.pack(pady=6, padx=16, fill="x")
        tk.Label(fr_tam, text="Tamanho da fonte", bg=C["bg"], fg=C["texto"],
                 font=fonte_label).pack(side="left")
        self._var_tam = tk.IntVar(value=overlay._tam)
        sc = tk.Scale(fr_tam, from_=18, to=90, orient="horizontal",
                      variable=self._var_tam, command=self._mudar_tamanho,
                      bg=C["bg"], fg=C["texto"], troughcolor=C["painel"],
                      activebackground=C["btn_h"], highlightthickness=0,
                      length=120, showvalue=True, font=fonte_small)
        sc.pack(side="right")

        tk.Frame(self, bg="#222", height=1, width=240).pack(pady=8)

        # Posição manual
        tk.Label(self, text="Posição (X, Y)", bg=C["bg"], fg=C["texto"],
                 font=fonte_label).pack()
        fr_pos = tk.Frame(self, bg=C["bg"]); fr_pos.pack(pady=4)

        x0, y0 = overlay.get_posicao()
        self._var_x = tk.IntVar(value=x0)
        self._var_y = tk.IntVar(value=y0)

        tk.Label(fr_pos, text="X:", bg=C["bg"], fg=C["cinza"], font=fonte_small).grid(row=0, column=0, padx=4)
        tk.Spinbox(fr_pos, from_=0, to=3840, textvariable=self._var_x,
                   width=6, font=fonte_small, bg=C["btn"], fg=C["texto"],
                   buttonbackground=C["btn"], relief="flat",
                   command=self._mudar_posicao).grid(row=0, column=1, padx=4)
        tk.Label(fr_pos, text="Y:", bg=C["bg"], fg=C["cinza"], font=fonte_small).grid(row=0, column=2, padx=4)
        tk.Spinbox(fr_pos, from_=0, to=2160, textvariable=self._var_y,
                   width=6, font=fonte_small, bg=C["btn"], fg=C["texto"],
                   buttonbackground=C["btn"], relief="flat",
                   command=self._mudar_posicao).grid(row=0, column=3, padx=4)

        tk.Button(self, text="Aplicar posição", command=self._mudar_posicao,
                  bg=C["vermelho"], fg=C["texto"], relief="flat",
                  activebackground=C["btn_h"], activeforeground=C["texto"],
                  font=fonte_small, cursor="hand2", bd=0,
                  highlightthickness=0, padx=10, pady=5).pack(pady=10)

    def _escolher_cor(self):
        cor = colorchooser.askcolor(color=self._overlay._cor, parent=self,
                                    title="Cor do overlay")[1]
        if cor:
            self._preview.config(bg=cor)
            self._overlay.set_cor(cor)

    def _mudar_tamanho(self, _=None):
        self._overlay.set_tamanho(self._var_tam.get())

    def _mudar_posicao(self):
        self._overlay.set_posicao(self._var_x.get(), self._var_y.get())


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Elden Ring Counter")
        self.geometry("280x480+10+10")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.attributes("-topmost", True)

        self.mortes      = _ler_count()
        self._detector   = None
        self._rodando    = False
        self._var_mortes = tk.StringVar(value=str(self.mortes))

        self._overlay = Overlay(self, self._var_mortes)
        self._overlay.withdraw()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _build_ui(self):
        tk.Label(self, text="ELDEN RING", bg=C["bg"], fg=C["ouro"],
                 font=tkfont.Font(family="Georgia", size=10, weight="bold",
                                  slant="italic")).pack(pady=(16, 0))
        tk.Frame(self, bg=C["ouro"], height=1, width=230).pack(pady=5)
        tk.Label(self, text="VOCÊ MORREU", bg=C["bg"], fg=C["vermelho"],
                 font=tkfont.Font(family="Georgia", size=20, weight="bold")).pack()
        tk.Frame(self, bg=C["ouro"], height=1, width=230).pack(pady=5)

        tk.Label(self, textvariable=self._var_mortes, bg=C["bg"], fg=C["texto"],
                 font=tkfont.Font(family="Georgia", size=56, weight="bold")).pack()
        tk.Label(self, text="mortes", bg=C["bg"], fg=C["cinza"],
                 font=tkfont.Font(family="Georgia", size=9, slant="italic")).pack()

        tk.Frame(self, bg="#222", height=1, width=230).pack(pady=8)

        self._var_st = tk.StringVar(value="● Parado")
        self._lbl_st = tk.Label(self, textvariable=self._var_st,
                                 bg=C["bg"], fg=C["cinza"],
                                 font=tkfont.Font(family="Georgia", size=8, slant="italic"))
        self._lbl_st.pack(pady=2)

        fr1 = tk.Frame(self, bg=C["bg"]); fr1.pack(pady=6)
        self._btn_ini = self._btn(fr1, "▶  INICIAR", self._iniciar, C["vermelho"], w=12)
        self._btn_ini.grid(row=0, column=0, padx=3)
        self._btn_par = self._btn(fr1, "■  PARAR",   self._parar,   C["btn"],      w=10)
        self._btn_par.grid(row=0, column=1, padx=3)

        fr2 = tk.Frame(self, bg=C["bg"]); fr2.pack(pady=2)
        self._btn(fr2, "+1",    self._mais,  C["btn"], w=5).grid(row=0, column=0, padx=2)
        self._btn(fr2, "−1",    self._menos, C["btn"], w=5).grid(row=0, column=1, padx=2)
        self._btn(fr2, "RESET", self._reset, C["btn"], w=7).grid(row=0, column=2, padx=2)

        tk.Frame(self, bg="#222", height=1, width=230).pack(pady=8)

        self._var_ov = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Mostrar overlay (só o número)",
                       variable=self._var_ov, command=self._toggle_overlay,
                       bg=C["bg"], fg=C["cinza"], selectcolor=C["painel"],
                       activebackground=C["bg"], activeforeground=C["texto"],
                       font=tkfont.Font(family="Georgia", size=8)).pack()

        self._var_top = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="Sempre no topo",
                       variable=self._var_top, command=self._toggle_top,
                       bg=C["bg"], fg=C["cinza"], selectcolor=C["painel"],
                       activebackground=C["bg"], activeforeground=C["texto"],
                       font=tkfont.Font(family="Georgia", size=8)).pack(pady=1)

        self._btn(self, "⚙  Configurar overlay", self._abrir_config_overlay,
                  C["btn"], w=24).pack(pady=6)

        tk.Frame(self, bg=C["ouro"], height=1, width=230).pack(pady=8)

    def _btn(self, parent, txt, cmd, cor, w=10):
        return tk.Button(parent, text=txt, command=cmd,
                         bg=cor, fg=C["texto"], relief="flat",
                         activebackground=C["btn_h"], activeforeground=C["texto"],
                         font=tkfont.Font(family="Georgia", size=9),
                         width=w, pady=6, cursor="hand2", bd=0,
                         highlightthickness=0)

    def _iniciar(self):
        if self._rodando:
            return
        self._rodando = True
        self._var_st.set("● Monitorando...")
        self._lbl_st.config(fg=C["verde"])
        self._btn_ini.config(bg="#1a3a1a")
        self._btn_par.config(bg=C["vermelho"])
        self._detector = Detector(on_morte=self._on_morte)
        self._detector.start()

    def _parar(self):
        if not self._rodando:
            return
        self._rodando = False
        if self._detector:
            self._detector.parar()
        self._var_st.set("● Parado")
        self._lbl_st.config(fg=C["cinza"])
        self._btn_ini.config(bg=C["vermelho"])
        self._btn_par.config(bg=C["btn"])

    def _on_morte(self, frame):
        self.mortes += 1
        _salvar(self.mortes)
        if os.path.isdir("save_img"):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"save_img/{ts}_{self.mortes}.png", frame)
        self.after(0, self._atualizar)
        self.after(0, self._flash)

    def _flash(self):
        self._var_st.set(f"☠  VOCÊ MORREU! ({self.mortes}x)")
        self._lbl_st.config(fg=C["vermelho2"])
        if self._rodando:
            self.after(3500, lambda: (
                self._var_st.set("● Monitorando..."),
                self._lbl_st.config(fg=C["verde"])
            ))

    def _mais(self):
        self.mortes += 1; _salvar(self.mortes); self._atualizar()

    def _menos(self):
        if self.mortes > 0:
            self.mortes -= 1; _salvar(self.mortes); self._atualizar()

    def _reset(self):
        self.mortes = 0; _salvar(0); self._atualizar()

    def _atualizar(self):
        self._var_mortes.set(str(self.mortes))

    def _toggle_overlay(self):
        if self._var_ov.get():
            self._overlay.deiconify()
        else:
            self._overlay.withdraw()

    def _toggle_top(self):
        self.attributes("-topmost", self._var_top.get())

    def _abrir_config_overlay(self):
        JanelaOverlay(self, self._overlay)

    def _fechar(self):
        if self._detector:
            self._detector.parar()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()