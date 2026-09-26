# -*- coding: utf-8 -*-
"""
CONTROL CENTER v3.2 TURBO (Universal Builder ver 1.5) - Trung tâm Điều khiển & Gỡ lỗi Chuyên dụng
==========================================================================
ver 1.5 (Tab 2 - BUILD PYTHON): CHỐNG "BUILD THÀNH CÔNG NHƯNG EXE THIẾU THƯ VIỆN"
  Sự cố gốc: NHAN_VIEC v1.6 build lúc Python dùng để build CHƯA cài pystray. Vì code để
  `import pystray` trong try/except, Nuitka âm thầm bỏ qua, exe vẫn "build thành công"
  nhưng chạy ra KHÔNG có icon khay hệ thống -> kéo theo một loạt lỗi khác.
  * ImportChecker     : quét MỌI import (cả trong hàm, trong try/except, cả các file .py phụ cùng
                        thư mục) rồi hỏi CHÍNH python.exe dùng để build xem có tìm thấy không.
                        Thiếu -> dừng lại TRƯỚC khi build, đề nghị pip install đúng tên gói.
  * Nuitka            : tự thêm --include-module cho thư viện bên thứ 3 bị import trong try/except
                        (nếu vì lý do nào đó không tìm thấy lúc build -> Nuitka báo lỗi rõ ràng
                        thay vì âm thầm bỏ qua).
  * BuildVerifier     : SAU khi build, đọc báo cáo Nuitka (mỗi exe 1 file riêng, không ghi đè nhau)
                        hoặc file warn-*.txt của PyInstaller -> thư viện nào không có trong exe
                        thì báo THẤT BẠI và KHÔNG tạo bộ cài (không phát hành bản hỏng).

v3.1 = v3 (UI cuộn + thanh ghim đáy + progress + log từng lần build) + BỘ TĂNG TỐC:

  TẬN DỤNG TỐI ĐA MÁY KHI ĐÓNG GÓI
  * HardwareProfile   : đo CPU/RAM/ổ đĩa/nguồn điện/power plan/Defender bằng Win32 API (ctypes, không cần psutil).
  * recommend_jobs()  : tự tính --jobs cho Nuitka theo số lõi VÀ RAM còn trống (LTO tốn RAM hơn) -> không swap.
  * ProcessRunner     : chạy trình biên dịch với ưu tiên ABOVE_NORMAL (Turbo) / BELOW_NORMAL (Tiết kiệm);
                        cl.exe/gcc/scons/ISCC là tiến trình con nên kế thừa ưu tiên.
  * SystemTuner       : chặn máy ngủ (SetThreadExecutionState) + chuyển power plan High Performance
                        trong lúc build, khôi phục khi xong (best-effort, không cần admin).
  * Build tăng dần    : mặc định KHÔNG --remove-output / --clean nữa -> ccache/clcache + thư mục .build được
                        tái dùng, lần build sau chỉ biên dịch phần thay đổi.
  * Nuitka            : --noinclude-pytest/setuptools/IPython-mode=nofollow (ít module phải biên dịch),
                        --onefile-no-compression (bỏ bước nén zstd khi kiểm thử), --python-flag=no_docstrings.
  * Inno Setup        : LZMA2 ĐA LUỒNG (LZMANumBlockThreads = số lõi) + LZMAUseSeparateProcess (tiến trình 64-bit),
                        4 mức nén: không nén / nhanh / cân bằng / nhỏ nhất.
  * PerformanceAdvisor: gợi ý cụ thể khi phát hiện Defender chưa loại trừ, dự án trong OneDrive/Dropbox,
                        đang chạy pin, ổ mạng/USB, ít RAM, LTO bật khi kiểm thử...  Nút "Loại trừ Defender" (UAC).
  * BuildHistory      : lưu thời gian từng mốc của các lần build trước -> thanh tiến độ chạy ĐỀU theo thời gian
                        thực + ETA "còn ~mm:ss" + so sánh nhanh/chậm hơn lần trước.

KIẾN TRÚC 3 LỚP
---------------
  [Cấu hình]  AppConfig               -> JSON tại %APPDATA%\\ControlCenter\\config.json
  [Dịch vụ]   PythonLocator           -> dò python.exe + kiểm tra Nuitka/PyInstaller
              NuitkaToolchain         -> chọn MSVC/Zig/MinGW64 và kiểm tra toolchain
              SystemProbe/HardwareProfile/DefenderHelper -> đo máy, kiểm tra loại trừ Defender
              PerformanceAdvisor/SystemTuner/BuildHistory -> gợi ý, tinh chỉnh hệ thống, lịch sử & ETA
              IsccLocator             -> dò ISCC.exe (Registry -> PATH -> ổ cứng CỐ ĐỊNH)
              LogAnalyzer             -> đọc zip AES, trích traceback cuối, gom lỗi trùng
              OllamaClient            -> gọi LLM cục bộ (streaming, urllib, huỷ được)
              BuildConfig / BuildCommandFactory -> "chụp" tuỳ chọn & sinh lệnh build
              InnoSetupBuilder        -> sinh .iss (UTF-8 BOM, nén đa luồng) và biên dịch bộ cài
              BuildFailureDiagnostics -> đọc log lỗi, gợi ý cách sửa tiếng Việt
              ProcessRunner           -> chạy tiến trình con (ưu tiên CPU), đọc log realtime, dừng được
              ProgressTracker         -> ước lượng % tiến độ từ log + lịch sử (thuần Python, test được)
              BuildLogWriter          -> ghi log từng lần build ra thư mục dự án
              BuildPipeline           -> build -> tìm thành phẩm -> Inno Setup (thread nền)
  [Giao diện] ScrollableFrame, ConsoleText, AnalyzerTab, BuilderTab, ControlCenterApp
              MainThreadDispatcher    -> cầu nối an toàn từ thread nền về luồng UI

NGUYÊN TẮC
----------
  * KHÔNG có tác vụ nặng nào chạy trên luồng UI (quét zip, gọi AI, build, ISCC, dò công cụ, dò máy).
  * Thread nền KHÔNG được đụng vào widget; chỉ gửi callback qua MainThreadDispatcher.
  * Toàn bộ tuỳ chọn build được chụp vào BuildConfig ngay khi bấm nút.
  * Mọi tinh chỉnh hệ thống là best-effort và LUÔN được khôi phục; không bao giờ làm hỏng build.

YÊU CẦU: Windows 10/11, Python 3.9+.   pip install pyzipper   (Nuitka/PyInstaller cài theo nhu cầu)
Với Python 3.13 x64 trên Windows: nên cài Visual Studio 2022 Build Tools
(Desktop development with C++ + Windows SDK) và dùng backend --msvc=latest.
"""
from __future__ import annotations

import ast
import ctypes
import json
import logging
import os
import queue
import re
import shlex
import shutil
import string
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

try:
    import winreg  # type: ignore[import]
except ImportError:  # Không phải Windows
    winreg = None  # type: ignore[assignment]

try:
    import pyzipper  # type: ignore[import]

    HAS_PYZIPPER = True
except ImportError:
    pyzipper = None  # type: ignore[assignment]
    HAS_PYZIPPER = False

IS_WINDOWS = sys.platform == "win32"
APP_TITLE = "Trung Tâm Điều Khiển & Gỡ Lỗi Chuyên Dụng - CAX Tri Phú"
APP_VERSION = "1.5.0.0"   # Universal Builder ver 1.5


def _duong_dan_tai_nguyen(ten_file: str) -> Optional[str]:
    """Tìm file tài nguyên (icon...) đặt cạnh script/exe đang chạy - dùng được cả khi chạy
    trực tiếp bằng python lẫn khi đã đóng gói bằng Nuitka (--include-data-files)."""
    for goc in (os.path.dirname(os.path.abspath(sys.argv[0])),
                os.path.dirname(os.path.abspath(__file__)),
                os.getcwd()):
        duong_dan = os.path.join(goc, ten_file)
        if os.path.isfile(duong_dan):
            return duong_dan
    return None

# Không bật cửa sổ CMD đen khi Control Center chạy dưới dạng .exe không console
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
# Mật khẩu zip KHÔNG còn hard-code: ưu tiên ô nhập -> biến môi trường này
ZIP_PASSWORD_ENV = "CC_ZIP_PASSWORD"

# Lớp ưu tiên tiến trình Windows (kế thừa xuống cl.exe / gcc / scons / ISCC)
PRIORITY_FLAGS = {
    "high": getattr(subprocess, "HIGH_PRIORITY_CLASS", 0x00000080),
    "above_normal": getattr(subprocess, "ABOVE_NORMAL_PRIORITY_CLASS", 0x00008000),
    "normal": getattr(subprocess, "NORMAL_PRIORITY_CLASS", 0x00000020),
    "below_normal": getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000),
}
PRIORITY_LABELS = {"high": "Cao", "above_normal": "Trên bình thường", "normal": "Bình thường", "below_normal": "Thấp"}

log = logging.getLogger("control_center")


# ============================================================================
#  ĐƯỜNG DẪN DỮ LIỆU, LOGGING, HIGH-DPI
# ============================================================================
def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") if IS_WINDOWS else None
    root = Path(base) if base else Path.home() / ".config"
    path = root / "ControlCenter"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path.home()
    return path


APP_DIR = app_data_dir()
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "control_center.log"
LEGACY_PY_CONFIG = Path.home() / ".control_center_build_config.txt"  # file cấu hình của bản cũ


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
    )


def enable_high_dpi() -> None:
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ============================================================================
#  TIỆN ÍCH CHUNG
# ============================================================================
def is_frozen() -> bool:
    """True khi Control Center đang chạy dưới dạng .exe (PyInstaller đặt sys.frozen, Nuitka đặt __compiled__)."""
    return bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def normalize_version(version: str) -> str:
    """'1.2' -> '1.2.0.0'; 'abc' -> '0.0.0.0'. Windows yêu cầu đúng 4 số."""
    parts = [p.strip() for p in (version or "").split(".")]
    nums = [p if p.isdigit() else "0" for p in parts][:4]
    nums += ["0"] * (4 - len(nums))
    return ".".join(nums)


_BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str, fallback: str = "app") -> str:
    """Tên file .exe an toàn: bỏ ký tự cấm, gộp khoảng trắng thành '_' (tránh lỗi đường dẫn có dấu cách)."""
    cleaned = _BAD_FILENAME_CHARS.sub("", name or "").strip().rstrip(".")
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or fallback


def split_args(raw: str) -> list[str]:
    """Tách chuỗi tham số bổ sung. Trên Windows, shlex chế độ POSIX sẽ 'nuốt' dấu '\\' của
    đường dẫn (C:\\data -> C:data) nên phải escape trước rồi mới tách."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if IS_WINDOWS:
        return shlex.split(raw.replace("\\", "\\\\"))
    return shlex.split(raw)


def child_env() -> dict[str, str]:
    """Buộc tiến trình con Python in UTF-8 ra pipe để log tiếng Việt/emoji không bị vỡ."""
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def run_quiet(cmd: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, env=child_env(),
    )


def py_literal(text: str) -> str:
    """Escape chuỗi để nhúng vào version_info.txt của PyInstaller (file đó được eval như mã Python)."""
    return (text or "").replace("\\", "\\\\").replace("'", "\\'")


def open_in_explorer(path: str) -> None:
    try:
        if IS_WINDOWS:
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        log.warning("Không mở được %s: %s", path, exc)


def fmt_elapsed(seconds: float) -> str:
    """125.3 -> '02:05'; 3725 -> '1:02:05'."""
    total = int(max(0.0, seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


# ============================================================================
#  CẤU HÌNH NGƯỜI DÙNG (JSON, nhớ mọi trường nhập)
# ============================================================================
@dataclass
class AppConfig:
    python_exe: str = ""
    iscc_path: str = ""
    last_log_folder: str = ""
    zip_password: str = ""          # chỉ lưu khi remember_password = True
    remember_password: bool = False
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:3b"
    compiler: str = "Nuitka"
    nuitka_backend: str = "msvc"    # msvc | auto | zig | mingw64 | clangcl
    build_mode: str = "onefile"     # onefile | standalone
    console_mode: str = "noconsole"  # console | noconsole
    uac_admin: bool = False
    clean_build: bool = False       # TURBO: mặc định giữ build/cache -> lần sau build tăng dần
    lto: bool = False
    tk_plugin: bool = True
    make_installer: bool = True
    open_when_done: bool = True
    details_expanded: bool = False  # ngăn "Chi tiết" ở Tab 2 đang mở hay đóng
    # ---- TURBO: hiệu năng máy ----
    perf_mode: str = "turbo"        # turbo | balanced | eco
    jobs: int = 0                   # 0 = tự động theo CPU/RAM
    high_priority: bool = True      # ưu tiên ABOVE_NORMAL cho tiến trình build
    keep_awake: bool = True         # chặn máy ngủ khi build
    power_plan: bool = True         # chuyển High Performance khi build, khôi phục sau
    onefile_compress: bool = True   # Nuitka onefile: nén payload (tắt = nhanh hơn, exe to hơn)
    slim_imports: bool = True       # --noinclude-pytest/setuptools/IPython-mode=nofollow
    no_docstrings: bool = False     # --python-flag=no_docstrings
    installer_compression: str = "balanced"  # none | fast | balanced | max
    # ---- nâng cấp / gỡ bản cũ (Inno Setup) ----
    close_apps_on_install: bool = True   # CloseApplications=force - tự đóng app đang chạy khi cài đè
    warn_on_downgrade: bool = True       # cảnh báo/chặn khi cài bản CŨ HƠN bản đang có trên máy
    obsolete_paths: list[str] = field(default_factory=list)  # đường dẫn tương đối trong {app} cần xoá trước khi cài (file/thư mục dư từ bản cũ)
    autostart_with_windows: bool = False  # Tab 2: đăng ký chạy cùng Windows (Task + Registry Run key trong Inno Setup)
    verify_imports: bool = True     # ver 1.5 - Tab 2: kiểm tra thư viện trước & sau khi build
    uninstall_old_versions: bool = True   # ver 1.5 - Tab 2: bộ cài tự gỡ sạch MỌI bản cũ (kể cả bản đặt tên khác)
    delete_old_dirs: bool = True          # ver 1.5 - xoá cả thư mục cài cũ còn sót (chỉ trong Program Files)
    old_version_names: list[str] = field(default_factory=list)  # tên hiển thị (tiền tố) / tên .exe cũ cần gỡ thêm
    # ---- metadata ----
    company: str = "Công an xã Tri Phú"
    product: str = "Công cụ Tự động hóa Nghiệp vụ"
    exe_name: str = ""              # trống -> tự sinh từ tên phần mềm
    version: str = "1.0.0.0"
    copyright: str = "© 2026 Mã Đức Hiển"
    extra_args: str = ""
    last_script: str = ""
    icon: str = ""
    data_files: list[str] = field(default_factory=list)
    data_dirs: list[str] = field(default_factory=list)
    # ---- Tab 3: đóng gói file .exe build sẵn từ Visual Studio 2022 (Release) bằng Inno Setup ----
    vs_exe_path: str = ""            # file .exe HOẶC thư mục Release (bin\\Release\\...)
    vs_icon: str = ""
    vs_company: str = "Công an xã Tri Phú"
    vs_product: str = "Công cụ Tự động hóa Nghiệp vụ"
    vs_version: str = "1.0.0.0"
    vs_copyright: str = "© 2026 Mã Đức Hiển"
    vs_iscc_path: str = r"E:\Program Files\Inno Setup 7\ISCC.exe"
    vs_installer_compression: str = "balanced"
    vs_close_apps_on_install: bool = True
    vs_warn_on_downgrade: bool = True
    vs_autostart_with_windows: bool = False
    vs_obsolete_paths: list[str] = field(default_factory=list)
    vs_data_files: list[str] = field(default_factory=list)
    vs_data_dirs: list[str] = field(default_factory=list)
    vs_arch64: bool = True
    vs_open_when_done: bool = True
    vs_details_expanded: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            known = {f.name for f in fields(cls)}
            for key, value in data.items():
                if key in known:
                    setattr(cfg, key, value)
        except FileNotFoundError:
            pass
        except Exception as exc:
            log.warning("Config hỏng, dùng mặc định: %s", exc)
        # Kế thừa python.exe đã cấu hình ở bản cũ
        if not cfg.python_exe and LEGACY_PY_CONFIG.is_file():
            try:
                cfg.python_exe = LEGACY_PY_CONFIG.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        return cfg

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("Không ghi được config: %s", exc)

    @property
    def effective_zip_password(self) -> str:
        return self.zip_password or os.environ.get(ZIP_PASSWORD_ENV, "")


# ============================================================================
#  DỊCH VỤ 1: DÒ PYTHON & CÔNG CỤ ĐÓNG GÓI
# ============================================================================
@dataclass
class PythonInfo:
    path: str
    version: str = ""
    bits: int = 64
    nuitka: str = ""        # phiên bản, "" = chưa cài
    pyinstaller: str = ""
    msvc: str = ""          # installationPath của VS Build Tools, được dò ở thread nền

    def describe(self) -> str:
        n = f"Nuitka {self.nuitka}" if self.nuitka else "Nuitka: CHƯA cài"
        p = f"PyInstaller {self.pyinstaller}" if self.pyinstaller else "PyInstaller: CHƯA cài"
        m = "MSVC: OK" if self.msvc else "MSVC: chưa thấy"
        return f"Python {self.version} ({self.bits}-bit)  |  {n}  |  {p}  |  {m}"


class NuitkaToolchain:
    """Chọn compiler có chủ đích thay vì để Nuitka rơi ngẫu nhiên vào Zig/MSYS2.

    Với Python 3.13 trên Windows, MSVC là đường đi ổn định nhất (và nhanh nhất nhờ clcache).
    MSYS2 UCRT64 đặt trong PATH không phải là bộ MinGW64 mà Nuitka kiểm soát, vì vậy
    log "Non downloaded winlibs-gcc ... is being ignored" không phải lỗi mã Python.
    """

    BACKENDS = ("msvc", "auto", "zig", "mingw64", "clangcl")

    @staticmethod
    def python_major_minor(info: PythonInfo) -> tuple[int, int]:
        try:
            major, minor = info.version.split(".")[:2]
            return int(major), int(minor)
        except (ValueError, AttributeError):
            return 0, 0

    @staticmethod
    def vswhere_path() -> Optional[str]:
        candidates = [shutil.which("vswhere.exe"),
                      os.path.join(os.environ.get("ProgramFiles(x86)", ""),
                                   "Microsoft Visual Studio", "Installer", "vswhere.exe"),
                      os.path.join(os.environ.get("ProgramFiles", ""),
                                   "Microsoft Visual Studio", "Installer", "vswhere.exe")]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    @classmethod
    def find_msvc(cls) -> Optional[str]:
        """Trả về installationPath của VS có workload VC tools, không chỉ kiểm tra cl.exe PATH."""
        if not IS_WINDOWS:
            return None
        if shutil.which("cl.exe"):
            return "PATH"
        vswhere = cls.vswhere_path()
        if not vswhere:
            return None
        try:
            result = run_quiet([
                vswhere, "-latest", "-products", "*",
                "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property", "installationPath",
            ], timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        path = result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else ""
        return path if path and os.path.isdir(path) else None

    @classmethod
    def preflight(cls, info: PythonInfo, backend: str) -> list[str]:
        errors: list[str] = []
        if backend not in cls.BACKENDS:
            errors.append(f"Backend Nuitka không hợp lệ: {backend}")
            return errors
        if not IS_WINDOWS:
            return errors
        if backend in ("msvc", "clangcl") and not info.msvc:
            errors.append(
                "Chưa tìm thấy Visual Studio Build Tools 2022 có workload C++. "
                "Cài 'Desktop development with C++' + Windows SDK rồi chọn lại backend MSVC/ClangCL."
            )
        major, minor = cls.python_major_minor(info)
        if backend == "auto" and (major, minor) >= (3, 13) and not info.msvc:
            errors.append(
                "Backend Tự động có thể rơi vào Zig và gây lỗi CRT với Python 3.13. "
                "Cài MSVC rồi chọn MSVC, hoặc dùng Python 3.12 cho MinGW64."
            )
        if backend == "zig" and info.bits != 64:
            errors.append("Backend Zig trên Windows chỉ hỗ trợ Python x64; Python hiện tại không phải 64-bit.")
        return errors

    @classmethod
    def command_args(cls, info: PythonInfo, backend: str) -> list[str]:
        """Biến lựa chọn giao diện thành cờ Nuitka chính thức."""
        if backend == "msvc":
            return ["--msvc=latest"]
        if backend == "zig":
            return ["--zig"]
        if backend == "mingw64":
            major, minor = cls.python_major_minor(info)
            args = ["--mingw64"]
            if (major, minor) >= (3, 13):
                args.append("--experimental=force-mingw64")
            return args
        if backend == "clangcl":
            return ["--clang"]
        if backend == "auto" and cls.python_major_minor(info) >= (3, 13) and info.msvc:
            return ["--msvc=latest"]
        return []  # auto: Nuitka tự chọn trên Python cũ hơn


class PythonLocator:
    """Tìm python.exe để chạy Nuitka/PyInstaller (bắt buộc khi Control Center đã bị đóng gói thành .exe)."""

    # Mỗi câu lệnh 1 dòng riêng (bản cũ viết "import ...; try:" trên cùng 1 dòng -> SyntaxError,
    # nên probe() từng bị thay bằng bản giả luôn báo "Đã nhận diện" dù Python CHƯA cài Nuitka).
    PROBE = (
        "import sys, json, struct\n"
        "def ver(name):\n"
        "    try:\n"
        "        from importlib import metadata\n"
        "        return metadata.version(name)\n"
        "    except Exception:\n"
        "        return ''\n"
        "print('@@PY@@' + json.dumps({'version': '%d.%d.%d' % sys.version_info[:3], "
        "'bits': struct.calcsize('P') * 8, 'nuitka': ver('nuitka'), 'pyinstaller': ver('pyinstaller')}))\n"
    )

    def __init__(self, settings: AppConfig):
        self.settings = settings

    def _get_system_drives(self) -> list[str]:
        """Lấy danh sách các ổ đĩa hiện có trên Windows (C:\, D:\, E:\,...)."""
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        return drives

    def candidates(self) -> list[str]:
        out: list[str] = []

        def add(p: Optional[str]) -> None:
            if not p:
                return
            p_str = str(p)
            # Loại bỏ WindowsApps alias giả lập của Microsoft
            if "WindowsApps" in p_str:
                return
            if os.path.isfile(p_str):
                abs_p = os.path.abspath(p_str)
                if abs_p not in out:
                    out.append(abs_p)

        # 1. Kiểm tra cấu hình lưu trong Settings (nếu file còn tồn tại)
        if self.settings.python_exe and os.path.isfile(self.settings.python_exe):
            add(self.settings.python_exe)

        # 2. Lấy từ PATH thông qua shutil.which
        for name in ("python", "python3", "py"):
            add(shutil.which(name))

        # 3. Quét Registry
        if hasattr(self, "_find_from_registry"):
            for reg_exe in self._find_from_registry():
                add(reg_exe)

        # 4. Quét tự động trên TẤT CẢ các ổ đĩa (C:\, D:\, E:\,...)
        for drive in self._get_system_drives():
            for base_dir in ("Program Files", "Program Files (x86)", ""):
                target_dir = Path(drive) / base_dir if base_dir else Path(drive)
                if target_dir.is_dir():
                    try:
                        for py_folder in target_dir.glob("Python3*"):
                            add(py_folder / "python.exe")
                    except PermissionError:
                        continue

        # 5. Quét thư mục AppData người dùng
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            py_base = Path(local) / "Programs" / "Python"
            if py_base.is_dir():
                for sub in py_base.glob("Python3*"):
                    add(sub / "python.exe")

        return out

    def probe(self, python_exe: str) -> Optional[PythonInfo]:
        if not os.path.isfile(python_exe):
            return None
            
        # Hỏi CHÍNH python.exe này: phiên bản, số bit và phiên bản Nuitka/PyInstaller THỰC SỰ đã cài.
        # (Bản trước luôn ghi "Đã nhận diện" -> Python chưa cài Nuitka vẫn qua được kiểm tra, rồi build
        # lỗi "No module named nuitka"; và không biết đúng phiên bản Nuitka để chọn cờ dòng lệnh.)
        try:
            r = run_quiet([python_exe, "-c", self.PROBE], timeout=30)
            payload = next((ln[6:] for ln in r.stdout.splitlines() if ln.startswith("@@PY@@")), "")
            if r.returncode == 0 and payload:
                data = json.loads(payload)
                return PythonInfo(
                    path=python_exe,
                    version=str(data.get("version", "")),
                    bits=int(data.get("bits", 64)),
                    nuitka=str(data.get("nuitka") or ""),
                    pyinstaller=str(data.get("pyinstaller") or ""),
                )
            log.info("Probe %s thất bại (mã %s): %s", python_exe, r.returncode, (r.stderr or "")[-300:])
        except Exception as exc:
            log.info("Probe %s thất bại: %s", python_exe, exc)
        return None

    def resolve(self) -> Optional[PythonInfo]:
        """python.exe đã cấu hình (nếu còn chạy được) luôn thắng; nếu không, ưu tiên bản đã cài Nuitka/PyInstaller."""
        configured = os.path.abspath(self.settings.python_exe) if self.settings.python_exe else ""
        fallback: Optional[PythonInfo] = None
        for cand in self.candidates():
            info = self.probe(cand)
            if not info:
                continue
            if cand == configured or info.nuitka or info.pyinstaller:
                fallback = info
                break
            fallback = fallback or info
        if fallback:
            fallback.msvc = NuitkaToolchain.find_msvc() or ""
        return fallback

    def remember(self, path: str) -> tuple[Optional[PythonInfo], str]:
        info = self.probe(path)
        if not info:
            return None, "File này không chạy được như python.exe (hoặc là alias của Microsoft Store)."
        info.msvc = NuitkaToolchain.find_msvc() or ""
        self.settings.python_exe = path
        self.settings.save()
        return info, ""

    @staticmethod
    def pip_install_command(python_exe: str, package: str) -> list[str]:
        return [python_exe, "-m", "pip", "install", "--upgrade", package]


# ============================================================================
#  DỊCH VỤ 1b (TURBO): ĐO MÁY, DEFENDER, GỢI Ý HIỆU NĂNG, TINH CHỈNH HỆ THỐNG, LỊCH SỬ
# ============================================================================
class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class SystemProbe:
    """Đọc thông số máy bằng Win32 API qua ctypes - không cần psutil, không tốn thời gian."""

    DRIVE_NAMES = {0: "ổ không rõ loại", 1: "đường dẫn không tồn tại", 2: "USB/ổ tháo rời",
                   3: "ổ cứng cố định", 4: "ổ mạng", 5: "CD/DVD", 6: "RAM disk"}
    CLOUD_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "box sync", "mega")
    _GUID_RE = re.compile(r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})\s*(?:\(([^)\r\n]*)\))?")

    @staticmethod
    def memory() -> tuple[float, float]:
        """(tổng RAM GB, RAM trống GB); (0, 0) nếu không đọc được."""
        if IS_WINDOWS:
            st = _MemoryStatusEx()
            st.dwLength = ctypes.sizeof(st)
            try:
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                    return st.ullTotalPhys / 2 ** 30, st.ullAvailPhys / 2 ** 30
            except (AttributeError, OSError):
                pass
            return 0.0, 0.0
        try:
            page = os.sysconf("SC_PAGE_SIZE")
            return (os.sysconf("SC_PHYS_PAGES") * page / 2 ** 30,
                    os.sysconf("SC_AVPHYS_PAGES") * page / 2 ** 30)
        except (ValueError, OSError, AttributeError):
            return 0.0, 0.0

    @staticmethod
    def on_battery() -> Optional[bool]:
        if not IS_WINDOWS:
            return None
        st = _SystemPowerStatus()
        try:
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
                return None
        except (AttributeError, OSError):
            return None
        return {0: True, 1: False}.get(int(st.ACLineStatus))

    @classmethod
    def drive_type(cls, path: str) -> tuple[int, str]:
        if not IS_WINDOWS:
            return 3, "ổ cục bộ"
        drive, _ = os.path.splitdrive(os.path.abspath(path))
        if drive.startswith("\\\\"):
            return 4, "ổ mạng (UNC)"
        try:
            code = int(ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive + "\\")))
        except (AttributeError, OSError):
            code = 0
        return code, cls.DRIVE_NAMES.get(code, "ổ không rõ loại")

    @classmethod
    def cloud_synced(cls, path: str) -> Optional[str]:
        """Tên dịch vụ đồng bộ (OneDrive/Dropbox/...) nếu đường dẫn nằm trong thư mục được đồng bộ."""
        low = os.path.normcase(os.path.abspath(path)).lower()
        for env_name in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
            root = os.environ.get(env_name)
            if root and low.startswith(os.path.normcase(os.path.abspath(root)).lower()):
                return "OneDrive"
        for marker in cls.CLOUD_MARKERS:
            if marker in low:
                return marker.title()
        return None

    @classmethod
    def active_power_scheme(cls) -> tuple[str, str]:
        """(GUID, tên) của power plan đang dùng; ('', '') nếu không đọc được."""
        if not IS_WINDOWS:
            return "", ""
        try:
            r = run_quiet(["powercfg", "/getactivescheme"], timeout=8)
        except Exception:
            return "", ""
        m = cls._GUID_RE.search(r.stdout or "")
        if not m:
            return "", ""
        return m.group(1).lower(), (m.group(2) or "").strip()

    @staticmethod
    def set_power_scheme(guid: str) -> bool:
        try:
            return run_quiet(["powercfg", "/setactive", guid], timeout=8).returncode == 0
        except Exception:
            return False


class DefenderHelper:
    """Windows Defender quét realtime từng file .c/.obj/.dll mà Nuitka sinh ra -> build chậm 1.5-3 lần.
    Lớp này KIỂM TRA đường dẫn đã được loại trừ chưa, và XIN quyền admin (UAC) để thêm loại trừ."""

    @staticmethod
    def cache_dirs() -> list[str]:
        local = os.environ.get("LOCALAPPDATA", "")
        if not local:
            return []
        return [os.path.join(local, "Nuitka"), os.path.join(local, "pyinstaller")]

    @staticmethod
    def exclusions() -> Optional[list[str]]:
        """Danh sách ExclusionPath hiện tại; None = không xác định (không có Defender / PowerShell lỗi)."""
        if not IS_WINDOWS:
            return None
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            return None
        try:
            r = run_quiet([ps, "-NoProfile", "-NonInteractive", "-Command",
                           "(Get-MpPreference).ExclusionPath -join [Environment]::NewLine"], timeout=25)
        except Exception as exc:
            log.info("Get-MpPreference thất bại: %s", exc)
            return None
        if r.returncode != 0:
            return None
        return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]

    @staticmethod
    def is_excluded(path: str, exclusions: list[str]) -> bool:
        p = os.path.normcase(os.path.abspath(path)).rstrip("\\/") + os.sep
        for ex in exclusions:
            e = os.path.normcase(os.path.expandvars(ex)).rstrip("\\/") + os.sep
            if p.startswith(e):
                return True
        return False

    @staticmethod
    def request_exclusion(paths: list[str]) -> bool:
        """Mở PowerShell với quyền Admin (hộp thoại UAC) để chạy Add-MpPreference."""
        if not IS_WINDOWS or not paths:
            return False
        quoted = ",".join("'" + p.replace("'", "''") + "'" for p in paths)
        script = (f"Add-MpPreference -ExclusionPath {quoted}; "
                  "Write-Host 'Da them loai tru Windows Defender cho cac thu muc build.'; Start-Sleep -Seconds 2")
        params = f'-NoProfile -ExecutionPolicy Bypass -Command "{script}"'
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", params, None, 1)
            return int(rc) > 32
        except (AttributeError, OSError) as exc:
            log.warning("ShellExecuteW runas thất bại: %s", exc)
            return False


@dataclass
class HardwareProfile:
    """Ảnh chụp phần cứng/môi trường tại thời điểm dò - dùng để tính --jobs, luồng nén và đưa gợi ý."""

    cpu: int = 1
    ram_total_gb: float = 0.0
    ram_free_gb: float = 0.0
    on_battery: Optional[bool] = None
    power_guid: str = ""
    power_name: str = ""
    drive_code: int = 3
    drive_name: str = ""
    disk_free_gb: float = 0.0
    cloud: Optional[str] = None
    defender_checked: bool = False
    defender_project: Optional[bool] = None   # None = không xác định
    defender_cache: Optional[bool] = None

    @classmethod
    def quick(cls) -> "HardwareProfile":
        """Chỉ CPU + RAM (tức thì, dùng được trên luồng UI)."""
        total, free = SystemProbe.memory()
        return cls(cpu=os.cpu_count() or 1, ram_total_gb=total, ram_free_gb=free)

    @classmethod
    def probe(cls, project_dir: str = "", check_defender: bool = False) -> "HardwareProfile":
        """Dò đầy đủ (powercfg ~0.1s, PowerShell Defender ~1-3s) -> CHỈ gọi trên thread nền."""
        hw = cls.quick()
        hw.on_battery = SystemProbe.on_battery()
        hw.power_guid, hw.power_name = SystemProbe.active_power_scheme()
        target = project_dir if project_dir and os.path.isdir(project_dir) else os.path.expanduser("~")
        hw.drive_code, hw.drive_name = SystemProbe.drive_type(target)
        try:
            hw.disk_free_gb = shutil.disk_usage(target).free / 2 ** 30
        except OSError:
            hw.disk_free_gb = 0.0
        hw.cloud = SystemProbe.cloud_synced(target) if project_dir else None
        if check_defender:
            hw.defender_checked = True
            ex = DefenderHelper.exclusions()
            if ex is not None:
                hw.defender_project = DefenderHelper.is_excluded(target, ex) if project_dir else None
                caches = DefenderHelper.cache_dirs()
                hw.defender_cache = all(DefenderHelper.is_excluded(c, ex) for c in caches) if caches else None
        return hw

    def summary(self) -> str:
        parts = [f"{self.cpu} lõi CPU"]
        if self.ram_total_gb:
            parts.append(f"RAM {self.ram_total_gb:.1f} GB (trống {self.ram_free_gb:.1f})")
        drive = self.drive_name or "ổ ?"
        if self.disk_free_gb:
            drive += f", trống {self.disk_free_gb:.0f} GB"
        parts.append(drive)
        if self.cloud:
            parts.append(f"⚠ trong thư mục {self.cloud}")
        if self.on_battery is not None:
            parts.append("nguồn: PIN ⚠" if self.on_battery else "nguồn: điện lưới")
        if self.power_name or self.power_guid:
            parts.append(f"power plan: {self.power_name or self.power_guid[:8]}")
        if self.defender_checked:
            def mark(v: Optional[bool]) -> str:
                return "✓" if v else ("✗" if v is False else "?")
            parts.append(f"Defender loại trừ: dự án {mark(self.defender_project)}, cache {mark(self.defender_cache)}")
        return " · ".join(parts)


def recommend_jobs(hw: Optional[HardwareProfile], perf_mode: str, lto: bool) -> int:
    """Số tiến trình biên dịch C song song cho Nuitka (--jobs).
    Turbo = toàn bộ lõi; Cân bằng = chừa 1 lõi; Tiết kiệm = nửa số lõi.
    Sau đó GIỚI HẠN THEO RAM: mỗi cl.exe/gcc trên module lớn ăn ~0,9 GB (LTO ~1,6 GB); tràn RAM -> swap -> chậm hơn ít luồng."""
    cpu = max(1, (hw.cpu if hw else 0) or os.cpu_count() or 1)
    if perf_mode == "eco":
        jobs = max(1, cpu // 2)
    elif perf_mode == "balanced":
        jobs = max(1, cpu - 1)
    else:
        jobs = cpu
    ram = hw.ram_total_gb if hw else 0.0
    if ram:
        per_job_gb = 1.6 if lto else 0.9
        jobs = min(jobs, max(1, int((ram - 2.0) // per_job_gb)))
    return max(1, min(256, jobs))


def installer_threads_for(hw: Optional[HardwareProfile], perf_mode: str, compression: str) -> int:
    """Số luồng LZMA2 cho Inno Setup (LZMANumBlockThreads, tối đa 32). ultra64 ăn ~0,75 GB/luồng -> giới hạn theo RAM."""
    cpu = max(1, (hw.cpu if hw else 0) or os.cpu_count() or 1)
    if perf_mode == "eco":
        threads = max(1, cpu // 2)
    elif perf_mode == "balanced":
        threads = max(1, cpu - 1)
    else:
        threads = cpu
    if compression == "max":
        ram = hw.ram_total_gb if hw else 0.0
        if ram:
            threads = min(threads, max(1, int((ram - 2.0) // 0.75)))
    return max(1, min(32, threads))


@dataclass
class PerfContext:
    """Những gì PerformanceAdvisor cần biết - tách khỏi BuildConfig để UI gọi được khi chưa có python.exe."""

    compiler: str = "Nuitka"
    backend: str = "msvc"
    lto: bool = False
    clean_build: bool = False
    onefile: bool = True
    onefile_compress: bool = True
    installer: bool = True
    installer_compression: str = "balanced"
    perf_mode: str = "turbo"
    jobs: int = 0
    power_plan_enabled: bool = True
    python_bits: int = 64
    project_dir: str = ""
    last_total: Optional[float] = None


class PerformanceAdvisor:
    """Biến số đo của HardwareProfile + tuỳ chọn build thành gợi ý CỤ THỂ, xếp theo mức ảnh hưởng."""

    FAST_PLANS = ("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "e9a42b02-d5df-448d-aa00-03f14749eb61")

    @classmethod
    def tips(cls, hw: Optional[HardwareProfile], c: PerfContext) -> list[str]:
        t: list[str] = []
        nuitka = c.compiler == "Nuitka"
        if hw:
            if hw.cloud:
                t.append(f"⚠ Dự án nằm trong thư mục {hw.cloud}: client đồng bộ quét từng file .c/.obj -> build chậm 2-5 lần. "
                         "Tạm dừng đồng bộ hoặc chuyển dự án ra ổ cục bộ (vd. D:\\Projects).")
            if hw.drive_code in (2, 4):
                t.append(f"⚠ Dự án đang ở {hw.drive_name}: I/O chậm. Sao chép về ổ SSD cục bộ trước khi build.")
            if hw.defender_checked and (hw.defender_project is False or hw.defender_cache is False):
                t.append("⚠ Windows Defender đang quét realtime thư mục dự án/cache build -> thường chậm 1.5-3 lần. "
                         "Bấm '🛡 Loại trừ Defender' (cần Admin, chỉ làm 1 lần).")
            if hw.on_battery:
                t.append("⚠ Đang chạy PIN: Windows hạ xung CPU. Cắm sạc để build nhanh hơn rõ rệt.")
            if hw.disk_free_gb and hw.disk_free_gb < 5:
                t.append(f"⚠ Ổ dự án chỉ còn {hw.disk_free_gb:.1f} GB trống; Nuitka standalone cần vài GB tạm. Dọn bớt trước khi build.")
            if hw.ram_total_gb and hw.ram_total_gb < 8 and nuitka:
                t.append("⚠ RAM < 8 GB: số luồng C đã được tự giới hạn theo RAM; tránh bật LTO trên máy này.")
            if c.power_plan_enabled is False and hw.power_guid and hw.power_guid not in cls.FAST_PLANS:
                t.append(f"💡 Power plan hiện tại là '{hw.power_name or 'Balanced'}'. Bật 'Power plan High Performance khi build' "
                         "để CPU giữ xung cao suốt quá trình biên dịch.")
        if nuitka and c.lto:
            t.append("💡 LTO làm biên dịch C chậm 2-4 lần và tốn RAM gấp đôi; chỉ bật cho bản phát hành cuối cùng.")
        if c.clean_build:
            t.append("💡 'Xoá build/cache sau khi xong' đang bật -> lần build sau phải biên dịch lại từ đầu "
                     "(mất ccache/clcache và thư mục .build). Tắt để build tăng dần.")
        if nuitka and c.backend in ("zig", "mingw64"):
            t.append("💡 Trên Windows, MSVC + clcache thường biên dịch nhanh hơn Zig/MinGW; cài Build Tools rồi chọn MSVC.")
        if nuitka and c.onefile and c.onefile_compress:
            t.append("💡 Chỉ kiểm thử? Tắt 'Nén payload onefile' để bỏ bước nén zstd (tiết kiệm 20-90 giây với app lớn).")
        if c.installer and c.installer_compression == "max":
            t.append("💡 Inno lzma2/ultra64 nén rất chậm; dùng 'Cân bằng' khi kiểm thử, 'Nhỏ nhất' cho bản phát hành.")
        if c.perf_mode == "eco":
            t.append("💡 Chế độ Tiết kiệm chỉ dùng nửa CPU với ưu tiên thấp; chuyển sang Turbo khi không cần làm việc khác.")
        if c.python_bits == 32:
            t.append("⚠ Python 32-bit giới hạn 2-4 GB RAM cho trình biên dịch; dùng Python 64-bit để build nhanh và ổn định.")
        if c.jobs and hw and c.jobs > hw.cpu * 2:
            t.append(f"⚠ Số luồng C ({c.jobs}) vượt xa số lõi ({hw.cpu}) -> tranh chấp CPU/RAM, KHÔNG nhanh hơn; đặt 0 để tự động.")
        if c.last_total:
            t.append(f"⏱ Lần build gần nhất cùng cấu hình: {fmt_elapsed(c.last_total)} - thanh tiến độ và ETA lần này dựa trên số đó.")
        if not t:
            t.append("✅ Cấu hình đã tối ưu cho máy này.")
        return t


class SystemTuner:
    """Tinh chỉnh HỆ THỐNG trong lúc build và KHÔI PHỤC khi xong (best-effort, không cần admin):
       * SetThreadExecutionState -> máy không ngủ/không ngắt giữa chừng (quan trọng với laptop cơ quan).
       * powercfg -> chuyển sang High Performance nếu máy có plan đó, trả lại plan cũ sau khi build.
    Phải gọi enter()/exit() trên CÙNG một thread (thread build) vì ExecutionState gắn với thread."""

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

    def __init__(self, keep_awake: bool, power_plan: bool, say: Callable[[str], None]):
        self.keep_awake = keep_awake and IS_WINDOWS
        self.power_plan = power_plan and IS_WINDOWS
        self.say = say
        self._awake = False
        self._prev_scheme = ""
        self._prev_name = ""

    def enter(self) -> None:
        if self.keep_awake:
            try:
                fn = ctypes.windll.kernel32.SetThreadExecutionState
                fn.argtypes = [ctypes.c_uint]
                fn.restype = ctypes.c_uint
                if fn(self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED):
                    self._awake = True
                    self.say("> [TURBO] Đã chặn máy ngủ trong lúc build.")
            except (AttributeError, OSError) as exc:
                log.info("SetThreadExecutionState lỗi: %s", exc)
        if self.power_plan:
            guid, name = SystemProbe.active_power_scheme()
            if guid and guid not in PerformanceAdvisor.FAST_PLANS:
                if SystemProbe.set_power_scheme(self.HIGH_PERF_GUID):
                    self._prev_scheme, self._prev_name = guid, name
                    self.say(f"> [TURBO] Power plan: '{name or guid}' -> High Performance (sẽ khôi phục khi xong).")
                else:
                    self.say("> [TURBO] Máy không có power plan High Performance (laptop Modern Standby) - bỏ qua bước này.")
            elif guid:
                self.say(f"> [TURBO] Power plan đang là '{name or guid}' - giữ nguyên.")

    def exit(self) -> None:
        if self._prev_scheme:
            ok = SystemProbe.set_power_scheme(self._prev_scheme)
            label = self._prev_name or self._prev_scheme
            self.say(f"> [TURBO] Đã khôi phục power plan '{label}'." if ok
                     else "> [TURBO] Không khôi phục được power plan cũ - hãy kiểm tra Power Options.")
            self._prev_scheme = ""
        if self._awake:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            except (AttributeError, OSError):
                pass
            self._awake = False


class BuildHistory:
    """Lưu thời gian từng mốc của các lần build (theo script + cấu hình) tại %APPDATA%\\ControlCenter\\build_history.json.
    Dùng để: (1) thanh tiến độ chạy đều theo thời gian thực thay vì đoán, (2) ETA, (3) so sánh nhanh/chậm hơn lần trước."""

    FILE = APP_DIR / "build_history.json"
    KEEP = 8

    @staticmethod
    def make_key(script: str, compiler: str, backend: str, build_mode: str, lto: bool, installer_tag: str) -> str:
        return "|".join([os.path.normcase(os.path.abspath(script)), compiler,
                         backend if compiler == "Nuitka" else "-", build_mode,
                         "lto" if lto else "nolto", f"inst-{installer_tag}"])

    @classmethod
    def _load(cls) -> dict:
        try:
            data = json.loads(cls.FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @classmethod
    def runs(cls, key: str) -> list[dict]:
        return list(cls._load().get(key, []))

    @classmethod
    def expected(cls, key: str) -> Optional[dict]:
        """{'total': trung vị 3 lần OK gần nhất, 'marks': mốc của lần OK cuối, 'marks_total': tổng của lần đó}."""
        ok_runs = [r for r in cls.runs(key) if r.get("ok") and r.get("total")]
        if not ok_runs:
            return None
        totals = sorted(float(r["total"]) for r in ok_runs[-3:])
        last = ok_runs[-1]
        return {"total": totals[len(totals) // 2], "marks": last.get("marks") or {},
                "marks_total": float(last["total"]), "jobs": last.get("jobs")}

    @classmethod
    def record(cls, key: str, ok: bool, total: float, marks: dict, jobs: int, perf_mode: str) -> None:
        try:
            data = cls._load()
            runs = data.get(key, [])
            runs.append({"when": datetime.now().isoformat(timespec="seconds"), "ok": ok, "total": round(total, 1),
                         "marks": {k: round(float(v), 1) for k, v in marks.items()}, "jobs": jobs, "perf": perf_mode})
            data[key] = runs[-cls.KEEP:]
            cls.FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            log.warning("Không ghi được lịch sử build: %s", exc)


# ============================================================================
#  DỊCH VỤ 2: DÒ INNO SETUP (ISCC.exe)
# ============================================================================
class IsccLocator:
    REGISTRY_KEYS = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1",
    )
    DRIVE_FIXED = 3  # GetDriveTypeW: chỉ quét ổ cứng cố định, bỏ ổ mạng/CD/USB (nguyên nhân treo bản cũ)

    @classmethod
    def fixed_drives(cls) -> list[str]:
        if not IS_WINDOWS:
            return []
        k32 = ctypes.windll.kernel32
        mask = k32.GetLogicalDrives()
        drives: list[str] = []
        for i, letter in enumerate(string.ascii_uppercase):
            if mask & (1 << i):
                root = f"{letter}:\\"
                if k32.GetDriveTypeW(ctypes.c_wchar_p(root)) == cls.DRIVE_FIXED:
                    drives.append(root)
        return drives

    @classmethod
    def from_registry(cls) -> Optional[str]:
        if winreg is None:
            return None
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in cls.REGISTRY_KEYS:
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        for value_name, is_dir in (("", False), ("InstallLocation", True), ("Inno Setup: App Path", True)):
                            try:
                                val, _ = winreg.QueryValueEx(key, value_name)
                            except FileNotFoundError:
                                continue
                            cand = os.path.join(val, "ISCC.exe") if is_dir else val
                            if cand and os.path.isfile(cand):
                                return cand
                except OSError:
                    continue
        return None

    @classmethod
    def scan_folders(cls) -> Optional[str]:
        roots: list[str] = []
        for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
            v = os.environ.get(env_name)
            if v:
                roots.append(v)
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots.append(os.path.join(local, "Programs"))
        for drive in cls.fixed_drives():
            roots += [os.path.join(drive, "Program Files"), os.path.join(drive, "Program Files (x86)")]
        seen: set[str] = set()
        for root in roots:
            key = os.path.normcase(root)
            if key in seen or not os.path.isdir(root):
                continue
            seen.add(key)
            try:
                for name in os.listdir(root):
                    if "inno setup" in name.lower():
                        cand = os.path.join(root, name, "ISCC.exe")
                        if os.path.isfile(cand):
                            return cand
            except OSError:
                continue
        return None

    @classmethod
    def find(cls, custom_path: str = "") -> Optional[str]:
        if custom_path and os.path.isfile(custom_path):
            return custom_path
        return cls.from_registry() or shutil.which("ISCC.exe") or cls.scan_folders()


# ============================================================================
#  DỊCH VỤ 3: PHÂN TÍCH LOG (zip AES) + GOM NHÓM LỖI
# ============================================================================
TRACEBACK_HEADER = "Traceback (most recent call last):"


@dataclass
class ErrorRecord:
    source: str     # tên file .zip (định danh máy trạm)
    member: str     # tên file log bên trong zip
    excerpt: str    # khối traceback CUỐI CÙNG (lỗi mới nhất) hoặc các dòng cuối
    signature: str  # dòng lỗi cuối cùng -> dùng để gom nhóm lỗi trùng giữa các máy


def extract_last_error(content: str, max_lines: int = 40) -> tuple[str, str]:
    lines = content.splitlines()
    start: Optional[int] = None
    for i in range(len(lines) - 1, -1, -1):
        if TRACEBACK_HEADER in lines[i]:
            start = i
            break
    if start is None:
        tail = [ln for ln in lines[-max_lines:] if ln.strip()]
        return "\n".join(tail), (tail[-1].strip() if tail else "")
    block: list[str] = []
    for ln in lines[start:]:
        block.append(ln)
        if len(block) > 1 and ln.strip() and not ln.startswith((" ", "\t")):
            break
    block = block[-max_lines:]
    return "\n".join(block), block[-1].strip()


class LogAnalyzer:
    def __init__(self, password: str, member_prefix: str = "error_log"):
        self.password = password.encode("utf-8") if password else None
        self.member_prefix = member_prefix.lower()

    @staticmethod
    def list_zips(folder: str) -> list[str]:
        return sorted(f for f in os.listdir(folder) if f.lower().endswith(".zip"))

    def read_zip(self, zip_path: str) -> list[ErrorRecord]:
        opener = pyzipper.AESZipFile if HAS_PYZIPPER else zipfile.ZipFile
        records: list[ErrorRecord] = []
        with opener(zip_path, "r") as zf:
            if self.password:
                zf.setpassword(self.password)
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if not os.path.basename(info.filename).lower().startswith(self.member_prefix):
                    continue
                text = zf.read(info.filename).decode("utf-8", errors="replace")
                excerpt, signature = extract_last_error(text)
                if excerpt.strip():
                    records.append(ErrorRecord(os.path.basename(zip_path), info.filename, excerpt, signature))
        return records

    def analyze(self, folder: str, report: Callable[[str, Optional[str]], None],
                cancel: threading.Event) -> list[ErrorRecord]:
        zips = self.list_zips(folder)
        if not zips:
            report("Không tìm thấy file .zip nào trong thư mục này.", "warn")
            return []
        report(f"Tìm thấy {len(zips)} file .zip. Bắt đầu giải mã...", "info")
        records: list[ErrorRecord] = []
        for idx, name in enumerate(zips, 1):
            if cancel.is_set():
                report("Đã dừng theo yêu cầu.", "warn")
                break
            prefix = f"[{idx}/{len(zips)}] {name}"
            try:
                found = self.read_zip(os.path.join(folder, name))
            except RuntimeError as exc:
                report(f"{prefix}: sai mật khẩu hoặc file mã hoá không hợp lệ ({exc})", "err")
                continue
            except (zipfile.BadZipFile, OSError, NotImplementedError) as exc:
                report(f"{prefix}: không đọc được ({exc})", "err")
                continue
            except Exception as exc:  # noqa: BLE001
                log.exception("Lỗi lạ khi đọc %s", name)
                report(f"{prefix}: lỗi không xác định ({exc})", "err")
                continue
            if not found:
                report(f"{prefix}: không có file {self.member_prefix}*", "warn")
                continue
            records.extend(found)
            for rec in found:
                report(f"--- {prefix} -> {rec.member} ---\n{rec.excerpt}\n", None)
        return records

    @staticmethod
    def group(records: list[ErrorRecord]) -> dict[str, list[ErrorRecord]]:
        groups: dict[str, list[ErrorRecord]] = {}
        for rec in records:
            groups.setdefault(rec.signature or "(không rõ)", []).append(rec)
        return dict(sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True))

    @staticmethod
    def build_prompt(groups: dict[str, list[ErrorRecord]], max_chars: int = 12000) -> str:
        parts = [
            "Bạn là chuyên gia Python. Dưới đây là các lỗi thu thập từ nhiều máy trạm, đã gom nhóm theo dòng lỗi cuối.",
            "Với MỖI nhóm hãy: (1) nêu nguyên nhân gốc ngắn gọn, (2) đưa đoạn code Python sửa lỗi, (3) cách phòng tránh.",
            "Trả lời bằng tiếng Việt, súc tích, ưu tiên nhóm gặp trên nhiều máy nhất.\n",
        ]
        for i, (_, recs) in enumerate(groups.items(), 1):
            machines = ", ".join(sorted({r.source for r in recs}))
            parts.append(f"### Nhóm {i} - gặp trên {len(recs)} máy ({machines})\n```\n{recs[0].excerpt}\n```\n")
        prompt = "\n".join(parts)
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n...(đã cắt bớt cho vừa cửa sổ ngữ cảnh của model)..."
        return prompt


# ============================================================================
#  DỊCH VỤ 4: OLLAMA (LLM cục bộ) - streaming, không cần requests
# ============================================================================
class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or "qwen2.5-coder:3b"

    def list_models(self, timeout: float = 5) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise OllamaError(f"Không kết nối được Ollama tại {self.base_url} ({exc}). Hãy mở ứng dụng Ollama.") from exc
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

    def generate_stream(self, prompt: str, on_token: Callable[[str], None],
                        cancel: threading.Event, num_ctx: int = 8192) -> str:
        payload = json.dumps({
            "model": self.model, "prompt": prompt, "stream": True,
            "options": {"num_ctx": num_ctx, "temperature": 0.2},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        chunks: list[str] = []
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                for raw in resp:
                    if cancel.is_set():
                        break
                    if not raw.strip():
                        continue
                    item = json.loads(raw.decode("utf-8"))
                    if item.get("error"):
                        raise OllamaError(item["error"])
                    token = item.get("response", "")
                    if token:
                        chunks.append(token)
                        on_token(token)
                    if item.get("done"):
                        break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise OllamaError(f"Model '{self.model}' chưa có. Chạy:  ollama pull {self.model}") from exc
            raise OllamaError(f"HTTP {exc.code}: {body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(f"Không kết nối được Ollama tại {self.base_url}. Hãy mở ứng dụng Ollama. ({exc.reason})") from exc
        except (OSError, ValueError) as exc:
            raise OllamaError(f"Lỗi khi nhận dữ liệu từ Ollama: {exc}") from exc
        return "".join(chunks)


# ============================================================================
#  DỊCH VỤ 5: CHẠY TIẾN TRÌNH CON (ưu tiên CPU, đọc log realtime, dừng được cả cây tiến trình)
# ============================================================================
class ProcessRunner:
    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def run(self, cmd: list[str], cwd: Optional[str], on_line: Callable[[str], None],
            priority: str = "normal") -> int:
        flags = CREATE_NO_WINDOW
        if IS_WINDOWS and priority in PRIORITY_FLAGS:
            flags |= PRIORITY_FLAGS[priority]   # cl.exe/gcc/scons/ISCC là tiến trình con -> kế thừa ưu tiên
        with self._lock:
            self._proc = subprocess.Popen(
                cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # không bao giờ treo vì chờ nhập y/N
                text=True, encoding="utf-8", errors="replace",
                creationflags=flags, env=child_env(),
            )
            proc = self._proc
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            on_line(line)
        proc.wait()
        with self._lock:
            self._proc = None
        return proc.returncode

    def terminate(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            if IS_WINDOWS:  # giết cả cây (Nuitka sinh thêm gcc/cl.exe, scons...)
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, creationflags=CREATE_NO_WINDOW)
            else:
                proc.terminate()
        except Exception as exc:
            log.warning("Không dừng được tiến trình %s: %s", proc.pid, exc)


# ============================================================================
#  DỊCH VỤ 6: CẤU HÌNH BUILD + SINH LỆNH NUITKA / PYINSTALLER
# ============================================================================
@dataclass
class BuildConfig:
    script: str
    python: PythonInfo
    compiler: str          # Nuitka | PyInstaller
    nuitka_backend: str    # msvc | auto | zig | mingw64 | clangcl
    build_mode: str        # onefile | standalone
    console_mode: str      # console | noconsole
    uac_admin: bool
    clean_build: bool
    lto: bool
    tk_plugin: bool
    icon: str
    data_files: list[str]
    data_dirs: list[str]
    company: str
    product: str
    exe_name: str
    version: str
    copyright: str
    extra_args: str
    make_installer: bool
    iscc_path: str
    # ---- TURBO ----
    perf_mode: str = "turbo"
    jobs: int = 0
    high_priority: bool = True
    keep_awake: bool = True
    power_plan: bool = True
    onefile_compress: bool = True
    slim_imports: bool = True
    no_docstrings: bool = False
    installer_compression: str = "balanced"
    close_apps_on_install: bool = True
    warn_on_downgrade: bool = True
    obsolete_paths: list[str] = field(default_factory=list)
    autostart_with_windows: bool = False
    hardware: Optional[HardwareProfile] = None
    # ---- ver 1.5: kiểm tra thư viện ----
    verify_imports: bool = True
    import_report: Optional["ImportReport"] = None   # kết quả ImportChecker ngay trước khi build
    uninstall_old_versions: bool = True
    delete_old_dirs: bool = True
    old_version_names: list[str] = field(default_factory=list)
    product_id: str = ""   # mã nhận diện sản phẩm cố định (đọc từ dòng # CC-PRODUCT-ID trong mã nguồn)

    # ---- thuộc tính dẫn xuất: MỘT nguồn sự thật cho mọi đường dẫn ----
    @property
    def script_dir(self) -> str:
        return os.path.dirname(os.path.abspath(self.script))

    @property
    def script_stem(self) -> str:
        return Path(self.script).stem

    @property
    def output_dir(self) -> str:
        return os.path.join(self.script_dir, "dist")

    @property
    def work_dir(self) -> str:
        return os.path.join(self.script_dir, "build")

    @property
    def log_dir(self) -> str:
        return os.path.join(self.script_dir, "build_logs")

    @property
    def installer_dir(self) -> str:
        return os.path.join(self.output_dir, "installer")

    @property
    def nuitka_report_path(self) -> str:
        """ver 1.5: mỗi exe 1 file báo cáo riêng - trước đây mọi dự án trong cùng thư mục ghi chung
        build\\nuitka-compilation-report.xml nên build GIAO_VIEC xong là mất báo cáo của NHAN_VIEC."""
        return os.path.join(self.work_dir, f"nuitka-report-{self.exe_stem}.xml")

    @property
    def pyinstaller_warn_path(self) -> str:
        return os.path.join(self.work_dir, self.exe_stem, f"warn-{self.exe_stem}.txt")

    @property
    def exe_stem(self) -> str:
        return sanitize_filename(self.exe_name or self.product, fallback=self.script_stem)

    @property
    def is_onefile(self) -> bool:
        return self.build_mode == "onefile"

    @property
    def no_console(self) -> bool:
        return self.console_mode == "noconsole"

    # ---- TURBO: giá trị hiệu lực ----
    @property
    def effective_jobs(self) -> int:
        if self.jobs > 0:
            return max(1, min(256, self.jobs))
        return recommend_jobs(self.hardware or HardwareProfile.quick(), self.perf_mode, self.lto)

    @property
    def priority_class(self) -> str:
        if self.perf_mode == "eco":
            return "below_normal"
        return "above_normal" if self.high_priority else "normal"

    @property
    def installer_threads(self) -> int:
        return installer_threads_for(self.hardware or HardwareProfile.quick(), self.perf_mode, self.installer_compression)

    @property
    def installer_tag(self) -> str:
        return self.installer_compression if self.make_installer else "off"

    @property
    def history_key(self) -> str:
        return BuildHistory.make_key(self.script, self.compiler, self.nuitka_backend, self.build_mode, self.lto, self.installer_tag)

    def perf_context(self) -> PerfContext:
        return PerfContext(
            compiler=self.compiler, backend=self.nuitka_backend, lto=self.lto, clean_build=self.clean_build,
            onefile=self.is_onefile, onefile_compress=self.onefile_compress, installer=self.make_installer,
            installer_compression=self.installer_compression, perf_mode=self.perf_mode, jobs=self.jobs,
            power_plan_enabled=self.power_plan, python_bits=self.python.bits, project_dir=self.script_dir,
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.script or not os.path.isfile(self.script):
            errors.append("Chưa chọn file Python gốc hợp lệ.")
        elif not self.script.lower().endswith((".py", ".pyw")):
            errors.append("File nguồn phải có đuôi .py hoặc .pyw.")
        if not re.fullmatch(r"\d+(\.\d+){3}", self.version):
            errors.append(f"Phiên bản '{self.version}' không đúng dạng x.x.x.x.")
        if self.icon and not os.path.isfile(self.icon):
            errors.append(f"File icon không tồn tại: {self.icon}")
        if self.icon and not self.icon.lower().endswith(".ico"):
            errors.append("Icon phải là file .ico.")
        for p in self.data_files:
            if not os.path.isfile(p):
                errors.append(f"File đính kèm không tồn tại: {p}")
        for d in self.data_dirs:
            if not os.path.isdir(d):
                errors.append(f"Thư mục đính kèm không tồn tại: {d}")
        if self.compiler == "Nuitka" and not self.python.nuitka:
            errors.append("Python đã chọn chưa cài Nuitka (bấm nút 'Cài Nuitka').")
        if self.compiler == "PyInstaller" and not self.python.pyinstaller:
            errors.append("Python đã chọn chưa cài PyInstaller (bấm nút 'Cài PyInstaller').")
        if self.compiler == "Nuitka":
            errors.extend(NuitkaToolchain.preflight(self.python, self.nuitka_backend))
            if self.nuitka_backend == "zig" and self.lto:
                errors.append("Zig + LTO làm lld-link thiếu ký hiệu CRT (frexpf, wmemchr...). "
                              "Bỏ tick 'Tối ưu LTO' hoặc chọn backend MSVC.")
        if self.perf_mode not in ("turbo", "balanced", "eco"):
            errors.append(f"Chế độ hiệu năng không hợp lệ: {self.perf_mode}")
        if not 0 <= self.jobs <= 256:
            errors.append("Số luồng biên dịch C phải từ 0 (tự động) đến 256.")
        if self.installer_compression not in InnoSetupBuilder.COMPRESSION:
            errors.append(f"Mức nén bộ cài không hợp lệ: {self.installer_compression}")
        try:
            split_args(self.extra_args)
        except ValueError as exc:
            errors.append(f"Tham số bổ sung không hợp lệ: {exc}")
        return errors

    def locate_artifact(self) -> Optional[str]:
        out = Path(self.output_dir)
        if self.is_onefile:
            for name in (f"{self.exe_stem}.exe", f"{self.script_stem}.exe"):
                if (out / name).is_file():
                    return str(out / name)
            exes = sorted(out.glob("*.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
            return str(exes[0]) if exes else None
        if self.compiler == "Nuitka":
            names = (f"{self.script_stem}.dist", f"{self.exe_stem}.dist")
        else:
            names = (self.exe_stem, self.script_stem)
        for name in names:
            if (out / name).is_dir():
                return str(out / name)
        return None

    def main_exe_in(self, artifact: str) -> str:
        if os.path.isfile(artifact):
            return os.path.basename(artifact)
        for name in (f"{self.exe_stem}.exe", f"{self.script_stem}.exe"):
            if os.path.isfile(os.path.join(artifact, name)):
                return name
        exes = [p.name for p in Path(artifact).glob("*.exe")]
        return exes[0] if exes else f"{self.exe_stem}.exe"


# ============================================================================
#  DỊCH VỤ: TỰ NHẬN DIỆN THƯ VIỆN CẦN PLUGIN/CỜ RIÊNG KHI ĐÓNG GÓI (Nuitka)
# ============================================================================
class DependencyScanner:
    """Quét các câu lệnh import ở cấp cao nhất trong file script (bằng ast, không
    thực thi code) để tự phát hiện thư viện cần --enable-plugin hoặc cờ include
    riêng khi build bằng Nuitka - tránh tình trạng build "thành công" nhưng file
    .exe chạy ra lại báo thiếu module (vd pywin32, PyQt5, numpy...).

    Đây chỉ quét import TRỰC TIẾP trong file được chọn để build (không lần theo
    các module .py phụ mà file đó tự import) - đủ dùng cho các tool 1-file như
    trong bộ này; nếu về sau tách nhiều file .py phụ, nên gộp thêm code quét đó."""

    # Tên module import (gốc, trước dấu chấm đầu tiên) -> tên plugin Nuitka chuẩn
    # (danh sách plugin chuẩn của Nuitka: xem `python -m nuitka --plugin-list`).
    # LƯU Ý: các module pywin32 (win32print, win32ui, pythoncom...) KHÔNG có mặt ở
    # đây - Nuitka không có plugin tên "pywin32", việc gói pywin32 do plugin bắt
    # buộc "implicit-imports" (luôn bật sẵn, không cần khai báo) tự lo; xem thêm
    # WIN32_MODULES bên dưới (chỉ dùng để ghi chú log, không sinh cờ build).
    KNOWN_PLUGINS: dict[str, str] = {
        "PyQt5": "pyqt5", "PyQt6": "pyqt6", "PySide2": "pyside2", "PySide6": "pyside6",
        "numpy": "numpy", "scipy": "numpy", "pandas": "numpy",
        "matplotlib": "numpy",  # plugin "numpy" của Nuitka gồm cả numpy/scipy/pandas/matplotlib
        "torch": "torch", "tensorflow": "tensorflow", "transformers": "transformers",
        "gi": "gi", "trio": "trio", "eventlet": "eventlet", "gevent": "gevent",
        "playwright": "playwright",
        "tkinter": "tk-inter", "customtkinter": "tk-inter",
    }

    # Các module pywin32 hay dùng - CHỈ để nhận diện và ghi chú vào log, KHÔNG sinh
    # cờ --enable-plugin (vì không có plugin đó); Nuitka tự gói qua implicit-imports.
    WIN32_MODULES: set[str] = {
        "win32print", "win32ui", "win32con", "win32api", "win32com", "win32comext",
        "win32gui", "win32event", "win32file", "win32process", "win32security",
        "win32clipboard", "win32pipe", "win32service", "win32serviceutil",
        "pythoncom", "pywintypes", "win32timezone",
    }

    # Tên module -> các cờ Nuitka khác (không phải --enable-plugin) cần thêm để
    # không thiếu dữ liệu/metadata của thư viện đó trong bản đóng gói
    KNOWN_EXTRA_FLAGS: dict[str, list[str]] = {
        "reportlab": ["--include-package-data=reportlab"],
        "pikepdf": ["--include-distribution-metadata=pikepdf"],
        "pypdf": ["--include-distribution-metadata=pypdf"],
        "customtkinter": ["--include-package=customtkinter",
                           "--include-package-data=customtkinter"],
    }

    @staticmethod
    def scan_top_level_modules(script_path: str) -> set[str]:
        """Trả về tập tên module được import trực tiếp trong file (import X / from X import Y)."""
        try:
            src = Path(script_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src, filename=script_path)
        except (OSError, SyntaxError, ValueError):
            return set()
        mods: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    mods.add(node.module.split(".")[0])
        return mods

    QT_MODULES: set[str] = {"PyQt5", "PyQt6", "PySide2", "PySide6"}
    TK_MODULES: set[str] = {"tkinter", "_tkinter", "customtkinter", "ttkbootstrap", "tkinterdnd2", "ttkthemes"}

    @classmethod
    def qt_only(cls, script_path: str) -> bool:
        """App giao diện Qt (PySide6/PyQt...) và KHÔNG dùng tkinter ở đâu cả (kể cả file .py phụ)?
        -> không bật plugin tk-inter: chỉ làm exe nặng thêm Tcl/Tk, và nếu Python build không cài
        Tcl/Tk thì Nuitka dừng hẳn với 'FATAL: tk-inter: Error, it seems tk-inter is not installed'."""
        uses, _ = ImportChecker.scan_sources(script_path)
        return bool(set(uses) & cls.QT_MODULES) and not (set(uses) & cls.TK_MODULES)

    @classmethod
    def suggest_nuitka_flags(cls, script_path: str, existing_plugins: set[str]) -> list[str]:
        """Trả về danh sách cờ Nuitka nên thêm (bỏ qua plugin đã có sẵn trong existing_plugins,
        vd tk-inter nếu người dùng đã tick checkbox riêng)."""
        mods = cls.scan_top_level_modules(script_path)
        plugins: set[str] = set()
        extra: list[str] = []
        for m in mods:
            plug = cls.KNOWN_PLUGINS.get(m)
            if plug and plug not in existing_plugins:
                plugins.add(plug)
            for flag in cls.KNOWN_EXTRA_FLAGS.get(m, []):
                if flag not in extra:
                    extra.append(flag)
        return [f"--enable-plugin={p}" for p in sorted(plugins)] + extra

    @classmethod
    def describe_detected(cls, script_path: str, existing_plugins: set[str]) -> list[str]:
        """Mô tả dễ đọc cho log: 'thư viện X -> --enable-plugin=Y'."""
        mods = cls.scan_top_level_modules(script_path)
        out: list[str] = []
        for m in sorted(mods):
            plug = cls.KNOWN_PLUGINS.get(m)
            if plug and plug not in existing_plugins:
                out.append(f"{m} -> --enable-plugin={plug}")
            for flag in cls.KNOWN_EXTRA_FLAGS.get(m, []):
                out.append(f"{m} -> {flag}")
        if mods & cls.WIN32_MODULES:
            out.append("(pywin32: win32api/win32print/pythoncom/... -> không cần cờ nào, Nuitka tự "
                        "gói qua plugin bắt buộc 'implicit-imports'; chỉ cần đảm bảo pywin32 đã cài "
                        "đúng trong Python dùng để build)")
        return out


# ============================================================================
#  DỊCH VỤ (ver 1.5): MÃ NHẬN DIỆN SẢN PHẨM CỐ ĐỊNH (nằm ngay trong mã nguồn)
# ============================================================================
class ProductIdentity:
    """Mã nhận diện một phần mềm XUYÊN SUỐT mọi phiên bản, dù đổi tên phần mềm, tên exe, tên file .py
    hay thư mục dự án. Lưu thành 1 dòng chú thích trong chính mã nguồn (không ảnh hưởng khi chạy):

# CC-PRODUCT-ID: 9F1C2E7A-3B4D-4C5E-8F60-1A2B3C4D5E6F  (mã nhận diện sản phẩm - GIỮ NGUYÊN qua mọi phiên bản, không chép sang phần mềm khác)

    Vì mã nguồn luôn được chép sang phiên bản sau (may_con_v1_6.py -> may_con_v2_0.py -> ...), mã đi
    theo phần mềm. AppId của bộ cài Inno Setup được sinh từ mã này -> Windows luôn coi mọi phiên bản là
    CÙNG MỘT phần mềm và bộ cài mới tự gỡ bản cũ.
    LƯU Ý: đừng chép mã này sang một phần mềm KHÁC - bộ cài của phần mềm đó sẽ gỡ nhầm phần mềm này."""

    MARKER = "CC-PRODUCT-ID"
    _READ_RE = re.compile(r"^[ \t]*#[ \t]*CC-PRODUCT-ID:[ \t]*([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
                          r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})", re.M)
    _VALID_RE = re.compile(r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}")

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4()).upper()

    @classmethod
    def normalize(cls, text: str) -> str:
        """'{9f1c...}' / ' 9f1c... ' -> '9F1C...'; không hợp lệ -> ''."""
        value = (text or "").strip().strip("{}").strip().upper()
        return value if cls._VALID_RE.fullmatch(value) else ""

    @classmethod
    def read(cls, script: str) -> str:
        try:
            text = Path(script).read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            return ""
        m = cls._READ_RE.search(text)
        return m.group(1).upper() if m else ""

    @classmethod
    def write(cls, script: str, product_id: str) -> None:
        """Chèn (hoặc thay) dòng mã vào đầu file, sau dòng #! / khai báo coding nếu có.
        Giữ nguyên BOM và kiểu xuống dòng của file."""
        raw = Path(script).read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
        nl = "\r\n" if "\r\n" in text else "\n"
        line = f"# {cls.MARKER}: {product_id}  (mã nhận diện sản phẩm - GIỮ NGUYÊN qua mọi phiên bản, không chép sang phần mềm khác)"
        if cls._READ_RE.search(text):
            text = re.sub(r"^[ \t]*#[ \t]*CC-PRODUCT-ID:.*$", line, text, count=1, flags=re.M)
        else:
            lines = text.split(nl)
            pos = 0
            while pos < min(2, len(lines)) and (lines[pos].startswith("#!")
                                                or re.match(r"^[ \t]*#.*coding[:=]", lines[pos])):
                pos += 1
            lines.insert(pos, line)
            text = nl.join(lines)
        Path(script).write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


class SourceVersion:
    """Số phiên bản mà CHÍNH PHẦN MỀM tự hiển thị / tự so khi tự cập nhật thường là 1 hằng trong mã
    nguồn (vd `VERSION = "1.6"` trong may_con). Ô 'Phiên bản' của Control Center chỉ ghi vào thuộc tính
    file exe + bộ cài -> nếu 2 nơi lệch nhau, phần mềm vẫn tự nhận là bản cũ (và cơ chế tự cập nhật so
    theo hằng này có thể cài lại liên tục). Lớp này dò & ghi hằng đó (chỉ dòng ở cấp module, cột 0)."""

    _RE = re.compile(r"^(VERSION|APP_VERSION|__version__)[ \t]*(?::[ \t]*str[ \t]*)?=[ \t]*(['\"])([^'\"\r\n]*)\2",
                     re.M)

    @classmethod
    def read(cls, script: str) -> Optional[tuple[str, str, int]]:
        """-> (tên hằng, giá trị, số dòng) hoặc None."""
        try:
            text = Path(script).read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            return None
        m = cls._RE.search(text)
        if not m:
            return None
        return m.group(1), m.group(3), text.count("\n", 0, m.start()) + 1

    @classmethod
    def write(cls, script: str, version: str) -> None:
        raw = Path(script).read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
        text, n = cls._RE.subn(lambda m: m.group(0)[: m.start(3) - m.start(0)] + version
                               + m.group(0)[m.end(3) - m.start(0):], text, count=1)
        if n:
            Path(script).write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))

    @staticmethod
    def same(a: str, b: str) -> bool:
        return normalize_version(a) == normalize_version(b)


# ============================================================================
#  DỊCH VỤ (ver 1.5): KIỂM TRA THƯ VIỆN TRƯỚC & SAU KHI BUILD
# ============================================================================
@dataclass
class ImportUse:
    """Một câu import trong mã nguồn."""
    file: str
    line: int
    guarded: bool   # nằm trong khối try (lỗi import bị nuốt -> exe chạy thiếu tính năng, không báo)
    lazy: bool      # nằm trong hàm/lớp (chỉ chạy khi gọi tới)
    dynamic: bool = False   # importlib.import_module("x") / __import__("x")

    def where(self) -> str:
        tags = [t for t, on in (("trong try/except", self.guarded), ("trong hàm", self.lazy),
                                ("import động", self.dynamic)) if on]
        return f"{os.path.basename(self.file)}:{self.line}" + (f" ({', '.join(tags)})" if tags else "")


@dataclass
class ModuleStatus:
    name: str
    kind: str = "unknown"   # stdlib | third_party | missing | error | local
    origin: str = ""
    uses: list[ImportUse] = field(default_factory=list)

    @property
    def guarded(self) -> bool:
        return bool(self.uses) and all(u.guarded for u in self.uses)

    @property
    def needs_force_include(self) -> bool:
        return any(u.guarded or u.dynamic for u in self.uses)

    @property
    def pip_name(self) -> str:
        return ImportChecker.PIP_NAMES.get(self.name, self.name)

    def first_use(self) -> str:
        return self.uses[0].where() if self.uses else ""


@dataclass
class ImportReport:
    python: str
    python_version: str = ""
    modules: dict[str, ModuleStatus] = field(default_factory=dict)
    local_files: list[str] = field(default_factory=list)
    error: str = ""

    def by_kind(self, *kinds: str) -> list[ModuleStatus]:
        return sorted((m for m in self.modules.values() if m.kind in kinds), key=lambda m: m.name.lower())

    def third_party(self) -> list[ModuleStatus]:
        return self.by_kind("third_party")

    def missing(self) -> list[ModuleStatus]:
        """Thư viện KHÔNG tìm thấy trong Python dùng để build (đã bỏ qua các module chỉ dành cho
        macOS/Linux mà code tự bọc try/except - trên Windows thiếu chúng là bình thường)."""
        return [m for m in self.by_kind("missing", "error")
                if not (m.guarded and m.name in ImportChecker.NON_WINDOWS_OPTIONAL)]

    def ignored_missing(self) -> list[ModuleStatus]:
        return [m for m in self.by_kind("missing", "error") if m not in self.missing()]

    def force_include_modules(self) -> list[str]:
        return [m.name for m in self.third_party() if m.needs_force_include]

    def pip_packages(self) -> list[str]:
        out: list[str] = []
        for m in self.missing():
            if m.pip_name not in out:
                out.append(m.pip_name)
        return out

    def summary_lines(self) -> list[str]:
        if self.error:
            return [f"⚠ Không kiểm tra được thư viện: {self.error}"]
        lines = [f"Python build: {self.python} ({self.python_version})"
                 + (f" · quét thêm {len(self.local_files) - 1} file .py phụ" if len(self.local_files) > 1 else "")]
        tp = self.third_party()
        if tp:
            lines.append("Thư viện bên thứ 3 có sẵn: " + ", ".join(
                m.name + (" (try/except → ép --include-module)" if m.needs_force_include else "") for m in tp))
        else:
            lines.append("Không dùng thư viện bên thứ 3 nào (chỉ thư viện chuẩn).")
        for m in self.missing():
            lines.append(f"✗ THIẾU '{m.name}' (pip install {m.pip_name}) - import tại {m.first_use()}")
        for m in self.ignored_missing():
            lines.append(f"· Bỏ qua '{m.name}' (chỉ dành cho macOS/Linux, code đã bọc try/except)")
        return lines


class _ImportVisitor(ast.NodeVisitor):
    """Duyệt AST, ghi lại MỌI câu import kèm ngữ cảnh: có nằm trong try không, trong hàm không.
    Khác DependencyScanner (chỉ lấy tên), ở đây cần ngữ cảnh để cảnh báo đúng mức."""

    def __init__(self, file: str):
        self.file = file
        self.try_depth = 0
        self.func_depth = 0
        self.found: list[tuple[str, ImportUse]] = []

    def _add(self, name: str, node: ast.AST, dynamic: bool = False) -> None:
        top = (name or "").split(".")[0].strip()
        if top and top.isidentifier() and top != "__main__":
            self.found.append((top, ImportUse(self.file, getattr(node, "lineno", 0), self.try_depth > 0 or dynamic,
                                              self.func_depth > 0, dynamic)))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(alias.name, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module:
            self._add(node.module, node)

    def visit_Try(self, node: ast.AST) -> None:
        self.try_depth += 1
        for child in node.body:  # type: ignore[attr-defined]
            self.visit(child)
        self.try_depth -= 1
        for child in list(node.handlers) + list(node.orelse) + list(node.finalbody):  # type: ignore[attr-defined]
            self.visit(child)

    visit_TryStar = visit_Try

    def _visit_scope(self, node: ast.AST) -> None:
        self.func_depth += 1
        self.generic_visit(node)
        self.func_depth -= 1

    visit_FunctionDef = visit_AsyncFunctionDef = visit_Lambda = _visit_scope

    def visit_If(self, node: ast.If) -> None:
        test = node.test
        name = test.id if isinstance(test, ast.Name) else (test.attr if isinstance(test, ast.Attribute) else "")
        if name == "TYPE_CHECKING":   # import chỉ để gợi ý kiểu, không chạy lúc thực thi
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        fname = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
        if fname in ("import_module", "__import__") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self._add(arg.value, node, dynamic=True)
        self.generic_visit(node)


class ImportChecker:
    """Trả lời câu hỏi: "Python dùng để build có ĐỦ mọi thư viện mà code cần không?"

    Nuitka/PyInstaller KHÔNG báo lỗi khi một thư viện import trong try/except bị thiếu lúc build:
    chúng chỉ lặng lẽ bỏ qua, exe vẫn build "thành công" rồi chạy ra thiếu tính năng (đúng sự cố
    NHAN_VIEC v1.6 thiếu pystray -> mất icon khay hệ thống). Lớp này:
      1. Quét AST của file chính + các file .py phụ cùng thư mục mà nó import (đệ quy).
      2. Gửi danh sách tên module sang CHÍNH python.exe dùng để build, hỏi importlib.util.find_spec
         (chỉ TÌM, không import/thực thi thư viện) -> phân loại chuẩn / bên thứ 3 / THIẾU.
    Chạy trong thread nền (gọi tiến trình con)."""

    # Tên import -> tên gói pip (chỉ liệt kê các trường hợp KHÁC tên)
    PIP_NAMES: dict[str, str] = {
        "PIL": "pillow", "cv2": "opencv-python", "yaml": "PyYAML", "docx": "python-docx",
        "pptx": "python-pptx", "fitz": "pymupdf", "pymupdf": "pymupdf", "sklearn": "scikit-learn",
        "bs4": "beautifulsoup4", "dateutil": "python-dateutil", "Crypto": "pycryptodome",
        "Cryptodome": "pycryptodomex", "serial": "pyserial", "usb": "pyusb", "OpenSSL": "pyOpenSSL",
        "jwt": "PyJWT", "magic": "python-magic", "dotenv": "python-dotenv", "pdfminer": "pdfminer.six",
        "win32api": "pywin32", "win32con": "pywin32", "win32gui": "pywin32", "win32print": "pywin32",
        "win32ui": "pywin32", "win32com": "pywin32", "win32comext": "pywin32", "win32event": "pywin32",
        "win32file": "pywin32", "win32process": "pywin32", "win32clipboard": "pywin32",
        "win32security": "pywin32", "win32service": "pywin32", "win32serviceutil": "pywin32",
        "win32pipe": "pywin32", "win32timezone": "pywin32", "pythoncom": "pywin32",
        "pywintypes": "pywin32", "winerror": "pywin32", "google": "google-api-python-client",
        "telegram": "python-telegram-bot", "Levenshtein": "python-Levenshtein", "zmq": "pyzmq",
        "skimage": "scikit-image", "attr": "attrs", "websocket": "websocket-client",
        "pypdfium2_raw": "pypdfium2", "tkinterdnd2": "tkinterdnd2", "ttkbootstrap": "ttkbootstrap",
    }

    # Module chỉ có trên macOS/Linux: thiếu trên Windows là bình thường nếu code đã bọc try/except
    NON_WINDOWS_OPTIONAL: set[str] = {
        "AppKit", "Foundation", "Quartz", "objc", "CoreFoundation", "PyObjCTools", "gi", "Xlib",
        "dbus", "evdev", "fcntl", "termios", "pwd", "grp", "posix", "resource", "readline", "curses",
    }

    MAX_LOCAL_FILES = 200

    _QUERY = r"""
import sys, json, os, importlib.util
names = json.loads(sys.argv[1])
std = set(getattr(sys, "stdlib_module_names", ())) | set(sys.builtin_module_names)
base = os.path.normcase(os.path.abspath(sys.base_prefix))
out = {}
for n in names:
    if n in std:
        out[n] = ["stdlib", ""]
        continue
    try:
        spec = importlib.util.find_spec(n)
    except Exception as e:
        out[n] = ["error", "%s: %s" % (type(e).__name__, e)]
        continue
    if spec is None:
        out[n] = ["missing", ""]
        continue
    origin = spec.origin or ""
    if not origin or origin == "namespace":
        locs = list(spec.submodule_search_locations or [])
        origin = locs[0] if locs else ""
    if origin in ("built-in", "frozen"):
        out[n] = ["stdlib", origin]
        continue
    low = os.path.normcase(os.path.abspath(origin)) if origin else ""
    in_site = "site-packages" in low or "dist-packages" in low
    kind = "stdlib" if (low.startswith(base) and not in_site) else "third_party"
    out[n] = [kind, origin]
print("@@CC@@" + json.dumps({"version": sys.version.split()[0], "result": out}))
"""

    @classmethod
    def scan_sources(cls, script: str) -> tuple[dict[str, list[ImportUse]], list[str]]:
        """Quét file chính + file .py/gói phụ cùng thư mục (đệ quy). Trả về (tên -> các lần import, các file đã quét)."""
        root = os.path.dirname(os.path.abspath(script))
        uses: dict[str, list[ImportUse]] = {}
        scanned: list[str] = []
        local_names: set[str] = set()
        queue_: list[str] = [os.path.abspath(script)]
        seen: set[str] = set()
        while queue_ and len(scanned) < cls.MAX_LOCAL_FILES:
            path = queue_.pop(0)
            key = os.path.normcase(path)
            if key in seen:
                continue
            seen.add(key)
            try:
                tree = ast.parse(Path(path).read_text(encoding="utf-8", errors="ignore"), filename=path)
            except (OSError, SyntaxError, ValueError):
                continue
            scanned.append(path)
            visitor = _ImportVisitor(path)
            visitor.visit(tree)
            for name, use in visitor.found:
                local = cls._local_target(root, name)
                if local:
                    local_names.add(name)
                    queue_.extend(local)
                    continue
                uses.setdefault(name, []).append(use)
        for name in local_names:
            uses.pop(name, None)
        return uses, scanned

    @staticmethod
    def _local_target(root: str, name: str) -> list[str]:
        """name là module/gói nằm cạnh script? -> danh sách file .py cần quét tiếp."""
        single = os.path.join(root, name + ".py")
        if os.path.isfile(single):
            return [single]
        pkg = os.path.join(root, name)
        if os.path.isfile(os.path.join(pkg, "__init__.py")):
            return [str(p) for p in sorted(Path(pkg).rglob("*.py"))[:100]]
        return []

    @classmethod
    def check(cls, script: str, python_exe: str) -> ImportReport:
        report = ImportReport(python=python_exe)
        uses, scanned = cls.scan_sources(script)
        report.local_files = scanned
        if not scanned:
            report.error = f"không đọc/phân tích được {os.path.basename(script)} (lỗi cú pháp?)"
            return report
        for name, lst in uses.items():
            report.modules[name] = ModuleStatus(name=name, uses=lst)
        if not uses:
            return report
        try:
            r = subprocess.run(
                [python_exe, "-c", cls._QUERY, json.dumps(sorted(uses))],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
                creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, env=child_env(),
                cwd=os.path.dirname(os.path.abspath(script)),
            )
            payload = next((ln[6:] for ln in r.stdout.splitlines() if ln.startswith("@@CC@@")), "")
            if not payload:
                report.error = (r.stderr or r.stdout or f"mã thoát {r.returncode}").strip()[-400:]
                return report
            data = json.loads(payload)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            report.error = str(exc)
            return report
        report.python_version = data.get("version", "")
        for name, (kind, origin) in data.get("result", {}).items():
            if name in report.modules:
                report.modules[name].kind = kind
                report.modules[name].origin = origin
        return report


class BuildVerifier:
    """Sau khi build: xác nhận MỌI thư viện bên thứ 3 mà code dùng đều thực sự nằm trong thành phẩm.
    Nuitka: đọc file --report (XML, liệt kê mọi module đã gói). PyInstaller: đọc warn-<tên>.txt."""

    _NOFOLLOW_RE = re.compile(r"--(?:nofollow-import-to|noinclude-custom-mode|exclude-module)[= ]([\w.,*]+)")
    _PYI_MISSING_RE = re.compile(r"^missing module named (.+?) - imported by", re.M)

    @classmethod
    def excluded_by_user(cls, cfg: BuildConfig) -> set[str]:
        out: set[str] = set()
        for m in cls._NOFOLLOW_RE.finditer(cfg.extra_args or ""):
            for part in m.group(1).split(","):
                out.add(part.split(".")[0].split(":")[0])
        if cfg.slim_imports and cfg.compiler == "Nuitka":
            out |= {"pytest", "_pytest", "setuptools", "IPython"}
        return out

    _NUITKA_MODULE_RE = re.compile(r'<module\s+name="([\w.]+)"')

    @classmethod
    def nuitka_modules(cls, report_path: str) -> Optional[set[str]]:
        # KHÔNG dùng xml.etree: Nuitka ghi các tham số có dấu tiếng Việt (vd --copyright=© ... Mã Đức Hiển)
        # sai mã hoá dù khai báo UTF-8 -> file XML "not well-formed", parser từ chối cả file.
        try:
            text = Path(report_path).read_bytes().decode("utf-8", errors="ignore")
        except OSError as exc:
            log.warning("Không đọc được báo cáo Nuitka %s: %s", report_path, exc)
            return None
        names = {m.group(1).split(".")[0] for m in cls._NUITKA_MODULE_RE.finditer(text)}
        return names or None

    @classmethod
    def pyinstaller_missing(cls, warn_path: str) -> Optional[set[str]]:
        try:
            text = Path(warn_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        out: set[str] = set()
        for m in cls._PYI_MISSING_RE.finditer(text):
            for part in m.group(1).split(","):
                out.add(part.strip().strip("'\"").split(".")[0])
        return out

    @classmethod
    def verify(cls, cfg: BuildConfig) -> tuple[list[str], list[str], str]:
        """-> (có trong exe, THIẾU trong exe, ghi chú nếu không kiểm tra được)."""
        report = cfg.import_report
        if report is None or report.error:
            return [], [], "bỏ qua (không có kết quả kiểm tra thư viện trước khi build)"
        skip = cls.excluded_by_user(cfg)
        expected = [m.name for m in report.third_party() if m.name not in skip]
        if not expected:
            return [], [], ""
        if cfg.compiler == "Nuitka":
            included = cls.nuitka_modules(cfg.nuitka_report_path)
            if included is None:
                return [], [], f"không đọc được báo cáo Nuitka {cfg.nuitka_report_path}"
            missing = [n for n in expected if n not in included]
        else:
            pyi_missing = cls.pyinstaller_missing(cfg.pyinstaller_warn_path)
            if pyi_missing is None:
                return [], [], f"không thấy {cfg.pyinstaller_warn_path}"
            missing = [n for n in expected if n in pyi_missing]
        return [n for n in expected if n not in missing], missing, ""


class BuildCommandFactory:
    @staticmethod
    def create(cfg: BuildConfig) -> list[str]:
        cmd = BuildCommandFactory._nuitka(cfg) if cfg.compiler == "Nuitka" else BuildCommandFactory._pyinstaller(cfg)
        cmd += split_args(cfg.extra_args)   # tham số người dùng đứng SAU -> ghi đè được --jobs/--lto của ta
        cmd.append(os.path.abspath(cfg.script))
        return cmd

    @staticmethod
    def _nuitka(cfg: BuildConfig) -> list[str]:
        major = int(cfg.python.nuitka.split(".")[0]) if cfg.python.nuitka[:1].isdigit() else 2
        cmd = [cfg.python.path, "-m", "nuitka", "--onefile" if cfg.is_onefile else "--standalone"]
        cmd += NuitkaToolchain.command_args(cfg.python, cfg.nuitka_backend)
        # TURBO: song song hoá biên dịch C theo số lõi & RAM (giai đoạn Python-level vốn đơn luồng)
        cmd.append(f"--jobs={cfg.effective_jobs}")
        if major >= 2:
            cmd.append("--windows-console-mode=" + ("disable" if cfg.no_console else "force"))
        else:
            cmd.append("--disable-console" if cfg.no_console else "--enable-console")
        if cfg.uac_admin:
            cmd.append("--windows-uac-admin")
        if cfg.clean_build:
            cmd.append("--remove-output")   # TURBO: mặc định TẮT -> giữ .build để Scons/ccache tái dùng
        cmd.append("--lto=yes" if cfg.lto else "--lto=no")
        if cfg.tk_plugin and not DependencyScanner.qt_only(cfg.script):
            cmd.append("--enable-plugin=tk-inter")
        if major >= 2:
            if cfg.slim_imports:  # ít module phải biên dịch -> nhanh & exe nhỏ hơn
                cmd += ["--noinclude-pytest-mode=nofollow", "--noinclude-setuptools-mode=nofollow",
                        "--noinclude-IPython-mode=nofollow"]
            if cfg.is_onefile and not cfg.onefile_compress:
                cmd.append("--onefile-no-compression")   # bỏ bước nén zstd payload
        if cfg.no_docstrings:
            cmd.append("--python-flag=no_docstrings")
        cmd += [
            "--assume-yes-for-downloads",
            "--no-progressbar",
            f"--output-dir={cfg.output_dir}",
            f"--output-filename={cfg.exe_stem}.exe",
            f"--report={cfg.nuitka_report_path}",
            f"--company-name={cfg.company}",
            f"--product-name={cfg.product}",
            f"--file-version={cfg.version}",
            f"--product-version={cfg.version}",
            f"--copyright={cfg.copyright}",
        ]
        if cfg.icon:
            cmd.append(f"--windows-icon-from-ico={cfg.icon}")
        for f in cfg.data_files:
            cmd.append(f"--include-data-files={f}={os.path.basename(f)}")
        for d in cfg.data_dirs:
            cmd.append(f"--include-data-dir={d}={os.path.basename(os.path.normpath(d))}")
        # TỰ ĐỘNG NHẬN DIỆN THƯ VIỆN CẦN PLUGIN/CỜ RIÊNG (vd pywin32, PyQt5, numpy...):
        # quét import trực tiếp trong file script và tự thêm cờ tương ứng, để tránh
        # tình trạng build "xong" nhưng file .exe chạy ra báo thiếu module.
        existing_plugins = {c.split("=", 1)[1] for c in cmd if c.startswith("--enable-plugin=")}
        for flag in DependencyScanner.suggest_nuitka_flags(cfg.script, existing_plugins):
            if flag not in cmd:
                cmd.append(flag)
        # ver 1.5: thư viện bên thứ 3 import trong try/except (vd pystray) -> ép --include-module.
        # Có sẵn thì vô hại; nếu lúc build lại không tìm thấy, Nuitka sẽ DỪNG VỚI LỖI rõ ràng
        # thay vì âm thầm bỏ qua rồi cho ra exe thiếu tính năng.
        if cfg.import_report is not None:
            for mod in cfg.import_report.force_include_modules():
                flag = f"--include-module={mod}"
                if flag not in cmd:
                    cmd.append(flag)
        return cmd

    @staticmethod
    def _pyinstaller(cfg: BuildConfig) -> list[str]:
        version_file = BuildCommandFactory.write_version_file(cfg)
        cmd = [
            cfg.python.path, "-m", "PyInstaller",
            "--noconfirm",
            "--onefile" if cfg.is_onefile else "--onedir",
            "--noconsole" if cfg.no_console else "--console",
            f"--name={cfg.exe_stem}",
            f"--distpath={cfg.output_dir}",
            f"--workpath={cfg.work_dir}",
            f"--specpath={cfg.work_dir}",
            f"--version-file={version_file}",
        ]
        if cfg.uac_admin:
            cmd.append("--uac-admin")
        if cfg.clean_build:
            cmd.append("--clean")   # TURBO: mặc định TẮT -> PyInstaller tái dùng cache phân tích
        if "upx" not in cfg.extra_args.lower():
            cmd.append("--noupx")   # UPX nén rất chậm và hay bị AV báo nhầm; ai cần thì thêm --upx-dir ở tham số
        if cfg.icon:
            cmd.append(f"--icon={cfg.icon}")
        for f in cfg.data_files:
            cmd.append(f"--add-data={f}{os.pathsep}.")
        for d in cfg.data_dirs:
            cmd.append(f"--add-data={d}{os.pathsep}{os.path.basename(os.path.normpath(d))}")
        if cfg.import_report is not None:   # ver 1.5: như --include-module bên Nuitka
            for mod in cfg.import_report.force_include_modules():
                cmd.append(f"--hidden-import={mod}")
        return cmd

    @staticmethod
    def write_version_file(cfg: BuildConfig) -> str:
        os.makedirs(cfg.work_dir, exist_ok=True)
        nums = ", ".join(cfg.version.split("."))
        content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nums}), prodvers=({nums}), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{py_literal(cfg.company)}'),
      StringStruct('FileDescription', '{py_literal(cfg.product)}'),
      StringStruct('FileVersion', '{cfg.version}'),
      StringStruct('InternalName', '{py_literal(cfg.exe_stem)}'),
      StringStruct('LegalCopyright', '{py_literal(cfg.copyright)}'),
      StringStruct('OriginalFilename', '{py_literal(cfg.exe_stem)}.exe'),
      StringStruct('ProductName', '{py_literal(cfg.product)}'),
      StringStruct('ProductVersion', '{cfg.version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
        path = os.path.join(cfg.work_dir, "version_info.txt")
        Path(path).write_text(content, encoding="utf-8")
        return path


# ============================================================================
#  DỊCH VỤ 7: INNO SETUP (nén LZMA2 đa luồng trong tiến trình 64-bit riêng)
# ============================================================================
class InnoSetupBuilder:
    COMPRESSION = {"none": "none", "fast": "lzma2/fast", "balanced": "lzma2/normal", "max": "lzma2/ultra64"}
    COMPRESSION_LABELS = {
        "none": "Không nén (kiểm thử - nhanh tuyệt đối)",
        "fast": "Nhanh (lzma2/fast, đa luồng)",
        "balanced": "Cân bằng (lzma2/normal, đa luồng)",
        "max": "Nhỏ nhất (lzma2/ultra64, chậm)",
    }

    def __init__(self, iscc_exe: str, runner: ProcessRunner):
        self.iscc_exe = iscc_exe
        self.runner = runner

    @staticmethod
    def app_id(product: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, "controlcenter.caxtriphu." + product.strip().lower())).upper()

    @classmethod
    def app_id_for(cls, cfg) -> str:
        """ver 1.5: có mã nhận diện sản phẩm (Tab 2) -> AppId cố định theo mã đó, đổi tên thoải mái.
        Không có (bản cũ / Tab 3) -> giữ cách cũ: sinh từ tên phần mềm."""
        pid = ProductIdentity.normalize(getattr(cfg, "product_id", ""))
        if pid:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, "controlcenter.caxtriphu.product-id." + pid.lower())).upper()
        return cls.app_id(cfg.product)

    @classmethod
    def compression_block(cls, cfg: BuildConfig) -> str:
        algo = cls.COMPRESSION.get(cfg.installer_compression, "lzma2/normal")
        if algo == "none":
            return "Compression=none\nSolidCompression=no\n"
        # LZMANumBlockThreads: nén song song theo khối (mặc định của Inno = 1 luồng!)
        # LZMAUseSeparateProcess: nén trong islzma64.exe -> dùng được > 2 GB RAM dù ISCC là 32-bit
        return (f"Compression={algo}\nSolidCompression=yes\n"
                "LZMAUseSeparateProcess=yes\n"
                f"LZMANumBlockThreads={cfg.installer_threads}\n")

    @staticmethod
    def extra_files_block(data_files: list[str], data_dirs: list[str]) -> str:
        """Sinh thêm dòng [Files] cho tài nguyên KHÔNG nằm sẵn trong artifact chính
        (dùng cho Tab 3 - exe build tay bằng Visual Studo, không có bước embed dữ liệu
        như Nuitka/PyInstaller ở Tab 2)."""
        lines: list[str] = []
        for f in data_files or []:
            if os.path.isfile(f):
                lines.append(f'Source: "{f}"; DestDir: "{{app}}"; Flags: ignoreversion')
        for d in data_dirs or []:
            if os.path.isdir(d):
                name = os.path.basename(os.path.normpath(d))
                lines.append(f'Source: "{d}\\*"; DestDir: "{{app}}\\{name}"; '
                             "Flags: ignoreversion recursesubdirs createallsubdirs")
        return "\n".join(lines)

    @staticmethod
    def _pas(text: str) -> str:
        """Chuỗi Pascal: nháy đơn nhân đôi."""
        return "'" + (text or "").replace("'", "''") + "'"

    @classmethod
    def old_version_rules(cls, cfg, main_exe: str) -> tuple[list[str], list[str]]:
        """-> (tên file .exe cũ, tiền tố tên hiển thị cũ). Luôn gồm exe chính của bản đang build:
        mọi bản đã cài có cùng tên exe (NHAN_VIEC.exe) đều bị coi là bản cũ, dù tên phần mềm đổi."""
        exes: list[str] = [main_exe]
        prefixes: list[str] = []
        for raw in getattr(cfg, "old_version_names", []) or []:
            item = raw.strip().strip('"')
            if not item:
                continue
            if item.lower().endswith(".exe"):
                if item.lower() not in (e.lower() for e in exes):
                    exes.append(os.path.basename(item))
            elif item not in prefixes:
                prefixes.append(item)
        return exes, prefixes

    @classmethod
    def uninstall_old_code(cls, cfg, main_exe: str) -> str:
        """[Code] cho Tab 2 (ver 1.5): trước khi chép file, tìm trong khoá Uninstall (HKLM 64/32-bit
        + HKCU) MỌI bản Inno Setup cũ khớp tên exe / tiền tố tên hiển thị -> tắt tiến trình, gỡ im
        lặng, xoá lệnh tự khởi động trỏ vào thư mục cũ, xoá thư mục cũ còn sót (chỉ trong Program
        Files). Bao gồm cả kiểm tra hạ cấp trên TẤT CẢ các bản cũ tìm được."""
        exes, prefixes = cls.old_version_rules(cfg, main_exe)
        exe_checks = "\n".join(f"  if CompareText(FileName, {cls._pas(e)}) = 0 then Result := True;" for e in exes)
        dir_checks = "\n".join(f"  if FileExists(AddBackslash(Dir) + {cls._pas(e)}) then Result := True;" for e in exes)
        prefix_checks = "\n".join(f"  if CC_StartsText({cls._pas(p)}, DisplayName) then Result := True;"
                                  for p in prefixes) or "  { không có tiền tố tên nào }"
        kill_lines = "\n".join(f"  CC_Kill({cls._pas(e)});" for e in exes)
        downgrade = "True" if cfg.warn_on_downgrade else "False"
        delete_dirs = "True" if getattr(cfg, "delete_old_dirs", True) else "False"
        code = r"""
[Code]
const
  CC_UNINST = 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  CC_RUN = 'Software\Microsoft\Windows\CurrentVersion\Run';
  CC_NEW_VERSION = @@VERSION@@;
  CC_OWN_KEY = @@OWN_KEY@@;   { mục gỡ cài của CHÍNH sản phẩm này (AppId cố định theo mã nhận diện) }
  CC_CHECK_DOWNGRADE = @@DOWNGRADE@@;
  CC_DELETE_DIRS = @@DELETE_DIRS@@;

var
  CC_Roots: array of Integer;
  CC_Keys: TArrayOfString;

function CompareVersion(V1, V2: String): Integer;
var
  p1, p2, n1, n2: Integer;
begin
  Result := 0;
  while (V1 <> '') or (V2 <> '') do
  begin
    p1 := Pos('.', V1);
    if p1 = 0 then p1 := Length(V1) + 1;
    p2 := Pos('.', V2);
    if p2 = 0 then p2 := Length(V2) + 1;
    n1 := StrToIntDef(Copy(V1, 1, p1 - 1), 0);
    n2 := StrToIntDef(Copy(V2, 1, p2 - 1), 0);
    if n1 > n2 then begin Result := 1; Exit; end;
    if n1 < n2 then begin Result := -1; Exit; end;
    if p1 <= Length(V1) then V1 := Copy(V1, p1 + 1, Length(V1)) else V1 := '';
    if p2 <= Length(V2) then V2 := Copy(V2, p2 + 1, Length(V2)) else V2 := '';
  end;
end;

function CC_StartsText(const Prefix, S: String): Boolean;
begin
  Result := (Prefix <> '') and (Length(S) >= Length(Prefix)) and
            (CompareText(Copy(S, 1, Length(Prefix)), Prefix) = 0);
end;

function CC_EndsText(const Suffix, S: String): Boolean;
begin
  Result := (Length(S) >= Length(Suffix)) and
            (CompareText(Copy(S, Length(S) - Length(Suffix) + 1, Length(Suffix)), Suffix) = 0);
end;

function CC_IsOldExe(const FileName: String): Boolean;
begin
  Result := False;
  if FileName = '' then Exit;
@@EXE_CHECKS@@
end;

function CC_DirHasOldExe(const Dir: String): Boolean;
begin
  Result := False;
  if Dir = '' then Exit;
@@DIR_CHECKS@@
end;

function CC_HasOldPrefix(const DisplayName: String): Boolean;
begin
  Result := False;
  if DisplayName = '' then Exit;
@@PREFIX_CHECKS@@
end;

function CC_IconExe(S: String): String;
begin
  S := RemoveQuotes(Trim(S));
  if CC_EndsText(',0', S) then S := Copy(S, 1, Length(S) - 2);
  Result := ExtractFileName(S);
end;

function CC_AppPath(RootKey: Integer; const Key: String): String;
begin
  Result := '';
  if not RegQueryStringValue(RootKey, Key, 'Inno Setup: App Path', Result) then
    RegQueryStringValue(RootKey, Key, 'InstallLocation', Result);
  Result := RemoveQuotes(Trim(Result));
end;

function CC_IsOldEntry(RootKey: Integer; const SubKey: String): Boolean;
var
  Key, DisplayName, Icon: String;
begin
  Result := False;
  if not CC_EndsText('_is1', SubKey) then Exit;   { chỉ gỡ bản do Inno Setup cài (biết chắc cờ gỡ im lặng) }
  if CompareText(SubKey, CC_OWN_KEY) = 0 then
  begin
    Result := True;   { cùng mã nhận diện sản phẩm -> chắc chắn là bản cũ, dù tên/exe đã đổi hoàn toàn }
    Exit;
  end;
  Key := CC_UNINST + '\' + SubKey;
  DisplayName := '';
  Icon := '';
  RegQueryStringValue(RootKey, Key, 'DisplayName', DisplayName);
  RegQueryStringValue(RootKey, Key, 'DisplayIcon', Icon);
  Result := CC_IsOldExe(CC_IconExe(Icon)) or CC_HasOldPrefix(DisplayName) or
            CC_DirHasOldExe(CC_AppPath(RootKey, Key));
end;

procedure CC_ScanRoot(RootKey: Integer);
var
  Names: TArrayOfString;
  I, N: Integer;
begin
  if not RegGetSubkeyNames(RootKey, CC_UNINST, Names) then Exit;
  for I := 0 to GetArrayLength(Names) - 1 do
    if CC_IsOldEntry(RootKey, Names[I]) then
    begin
      N := GetArrayLength(CC_Keys);
      SetArrayLength(CC_Keys, N + 1);
      SetArrayLength(CC_Roots, N + 1);
      CC_Keys[N] := Names[I];
      CC_Roots[N] := RootKey;
    end;
end;

procedure CC_FindOldVersions;
begin
  SetArrayLength(CC_Keys, 0);
  SetArrayLength(CC_Roots, 0);
  if IsWin64 then
  begin
    CC_ScanRoot(HKLM64);
    CC_ScanRoot(HKLM32);
  end
  else
    CC_ScanRoot(HKLM);
  CC_ScanRoot(HKCU);
end;

procedure CC_Kill(const ExeName: String);
var
  RC: Integer;
begin
  if ExeName = '' then Exit;
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM "' + ExeName + '"', '', SW_HIDE,
       ewWaitUntilTerminated, RC);
end;

procedure CC_CleanRunRoot(RootKey: Integer; const OldDir: String);
var
  Names: TArrayOfString;
  I: Integer;
  Data: String;
begin
  if OldDir = '' then Exit;
  if not RegGetValueNames(RootKey, CC_RUN, Names) then Exit;
  for I := 0 to GetArrayLength(Names) - 1 do
    if RegQueryStringValue(RootKey, CC_RUN, Names[I], Data) then
      if Pos(Lowercase(AddBackslash(OldDir)), Lowercase(Data)) > 0 then
      begin
        Log('Xoa lenh tu khoi dong cu: ' + Names[I] + ' = ' + Data);
        RegDeleteValue(RootKey, CC_RUN, Names[I]);
      end;
end;

procedure CC_CleanRunKeys(const OldDir: String);
begin
  CC_CleanRunRoot(HKCU, OldDir);
  if IsWin64 then
  begin
    CC_CleanRunRoot(HKLM64, OldDir);
    CC_CleanRunRoot(HKLM32, OldDir);
  end
  else
    CC_CleanRunRoot(HKLM, OldDir);
end;

function CC_IsUnder(const Dir, Base: String): Boolean;
begin
  Result := (Base <> '') and CC_StartsText(AddBackslash(Base), AddBackslash(Dir)) and
            (CompareText(AddBackslash(Base), AddBackslash(Dir)) <> 0);
end;

function CC_SafeToDelete(const Dir: String): Boolean;
begin
  Result := CC_IsUnder(Dir, ExpandConstant('{commonpf32}')) or
            CC_IsUnder(Dir, ExpandConstant('{localappdata}') + '\Programs');
  if (not Result) and IsWin64 then
    Result := CC_IsUnder(Dir, ExpandConstant('{commonpf64}'));
end;

function InitializeSetup(): Boolean;
var
  I: Integer;
  V, Newest: String;
begin
  Result := True;
  if not CC_CHECK_DOWNGRADE then Exit;
  CC_FindOldVersions;
  Newest := '';
  for I := 0 to GetArrayLength(CC_Keys) - 1 do
    if RegQueryStringValue(CC_Roots[I], CC_UNINST + '\' + CC_Keys[I], 'DisplayVersion', V) then
      if CompareVersion(V, Newest) > 0 then Newest := V;
  if (Newest <> '') and (CompareVersion(Newest, CC_NEW_VERSION) > 0) then
  begin
    if WizardSilent then
      Result := False
    else
      Result := (MsgBox('May dang co phien ban MOI HON (' + Newest + ') so voi ban cai nay (' + CC_NEW_VERSION + ').' + #13#10 +
        'Ban co chac chan muon cai DE bang ban CU HON khong?', mbConfirmation, MB_YESNO) = IDYES);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  I, RC, Tries: Integer;
  Key, Cmd, OldDir, Icon: String;
begin
  Result := '';
@@KILL_LINES@@
  CC_FindOldVersions;
  for I := 0 to GetArrayLength(CC_Keys) - 1 do
  begin
    Key := CC_UNINST + '\' + CC_Keys[I];
    OldDir := CC_AppPath(CC_Roots[I], Key);
    Icon := '';
    if RegQueryStringValue(CC_Roots[I], Key, 'DisplayIcon', Icon) then
      CC_Kill(CC_IconExe(Icon));
    Cmd := '';
    RegQueryStringValue(CC_Roots[I], Key, 'UninstallString', Cmd);
    Cmd := RemoveQuotes(Trim(Cmd));
    Log('Go ban cu: ' + CC_Keys[I] + ' | ' + OldDir + ' | ' + Cmd);
    if (Cmd <> '') and FileExists(Cmd) then
    begin
      Exec(Cmd, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, RC);
      Tries := 0;
      while RegKeyExists(CC_Roots[I], Key) and (Tries < 60) do
      begin
        Sleep(500);
        Tries := Tries + 1;
      end;
    end
    else
      RegDeleteKeyIncludingSubkeys(CC_Roots[I], Key);   { mục gỡ cài mồ côi: file gỡ cài đã mất }
    CC_CleanRunKeys(OldDir);
    if CC_DELETE_DIRS and (OldDir <> '') and DirExists(OldDir) and CC_SafeToDelete(OldDir) then
    begin
      Log('Xoa thu muc cu con sot: ' + OldDir);
      DelTree(OldDir, True, True, True);
    end;
  end;
end;
"""
        own_key = "{" + cls.app_id_for(cfg) + "}_is1"
        return (code.replace("@@VERSION@@", cls._pas(cfg.version))
                .replace("@@OWN_KEY@@", cls._pas(own_key))
                .replace("@@DOWNGRADE@@", downgrade)
                .replace("@@DELETE_DIRS@@", delete_dirs)
                .replace("@@EXE_CHECKS@@", exe_checks)
                .replace("@@DIR_CHECKS@@", dir_checks)
                .replace("@@PREFIX_CHECKS@@", prefix_checks)
                .replace("@@KILL_LINES@@", kill_lines))

    @classmethod
    def render(cls, cfg: BuildConfig, artifact: str, main_exe: str, extra_files: str = "") -> str:
        if os.path.isdir(artifact):
            files = f'Source: "{artifact}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs'
        else:
            files = f'Source: "{artifact}"; DestDir: "{{app}}"; Flags: ignoreversion'
        app_id_val = cls.app_id_for(cfg)
        app_id_line = "AppId={{" + app_id_val + "}"
        icon_line = f"SetupIconFile={cfg.icon}\n" if cfg.icon else ""
        arch_line = "ArchitecturesInstallIn64BitMode=x64\n" if cfg.python.bits == 64 else ""
        comp_block = cls.compression_block(cfg)

        # ---- tự đóng app đang chạy trước khi cài đè (tránh lỗi "file đang được sử dụng") ----
        close_apps_block = ""
        if cfg.close_apps_on_install:
            close_apps_block = "CloseApplications=force\nCloseApplicationsFilter=*.exe\nRestartApplications=yes\n"

        # ---- dọn file/thư mục dư từ bản cũ (khi cấu trúc file đổi giữa các phiên bản) ----
        install_delete_block = ""
        obsolete = [p.strip().strip("/\\") for p in (cfg.obsolete_paths or []) if p.strip()]
        if obsolete:
            del_lines = "\n".join(f'Type: filesandordirs; Name: "{{app}}\\{p}"' for p in obsolete)
            install_delete_block = f"\n[InstallDelete]\n{del_lines}\n"

        # ---- cảnh báo/chặn cài đè bằng bản CŨ HƠN bản đang có trên máy (chống hạ cấp nhầm) ----
        downgrade_code_block = ""
        if cfg.warn_on_downgrade:
            reg_key = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{" + app_id_val + "}_is1"
            downgrade_code_block = f"""
[Code]
function CompareVersion(V1, V2: String): Integer;
var
  p1, p2, n1, n2: Integer;
begin
  Result := 0;
  while (V1 <> '') or (V2 <> '') do
  begin
    p1 := Pos('.', V1);
    if p1 = 0 then p1 := Length(V1) + 1;
    p2 := Pos('.', V2);
    if p2 = 0 then p2 := Length(V2) + 1;
    n1 := StrToIntDef(Copy(V1, 1, p1 - 1), 0);
    n2 := StrToIntDef(Copy(V2, 1, p2 - 1), 0);
    if n1 > n2 then begin Result := 1; Exit; end;
    if n1 < n2 then begin Result := -1; Exit; end;
    if p1 <= Length(V1) then V1 := Copy(V1, p1 + 1, Length(V1)) else V1 := '';
    if p2 <= Length(V2) then V2 := Copy(V2, p2 + 1, Length(V2)) else V2 := '';
  end;
end;

function InitializeSetup(): Boolean;
var
  sPrevVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKLM, '{reg_key}', 'DisplayVersion', sPrevVersion) then
  begin
    if CompareVersion(sPrevVersion, '{cfg.version}') > 0 then
    begin
      if WizardSilent then
        Result := False
      else
        Result := (MsgBox('May dang co phien ban MOI HON (' + sPrevVersion + ') so voi ban cai nay ({cfg.version}).' + #13#10 +
          'Ban co chac chan muon cai DE bang ban CU HON khong?', mbConfirmation, MB_YESNO) = IDYES);
    end;
  end;
end;
"""

        # ---- ver 1.5 (Tab 2): tự gỡ sạch MỌI bản cũ, nhận diện theo tên exe chứ không theo AppId/tên
        # phần mềm (AppId sinh từ tên phần mềm -> đổi tên là thành "phần mềm khác", bản cũ nằm lại).
        # Khối này đã gồm kiểm tra hạ cấp (trên mọi bản cũ tìm được) nên thay cho khối ở trên.
        if getattr(cfg, "uninstall_old_versions", False):
            downgrade_code_block = cls.uninstall_old_code(cfg, main_exe)

        # ---- tự khởi động cùng Windows: Task (mặc định KHÔNG tick) + Registry Run key cho user hiện tại ----
        autostart_task_line = ""
        autostart_registry_block = ""
        if getattr(cfg, "autostart_with_windows", False):
            autostart_task_line = ('\nName: "autostart"; Description: "Khởi động cùng Windows"; '
                                    'GroupDescription: "Tuỳ chọn:"; Flags: unchecked')
            autostart_registry_block = (
                "\n[Registry]\n"
                'Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Run"; '
                f'ValueType: string; ValueName: "{cfg.product}"; '
                f'ValueData: """{{app}}\\{main_exe}"""; Flags: uninsdeletevalue; Tasks: autostart\n'
            )

        folder = sanitize_filename(cfg.product, fallback=cfg.exe_stem)
        # ver 1.5: AppId cố định theo mã sản phẩm -> Inno mặc định cài lại vào THƯ MỤC/NHÓM CŨ (vd
        # ...\NHAN_VIEC_V1.6 mãi mãi). Tắt để thư mục/Start Menu theo tên mới; tuỳ chọn Tasks vẫn nhớ.
        prev_block = ("UsePreviousAppDir=no\nUsePreviousGroup=no\n"
                      if ProductIdentity.normalize(getattr(cfg, "product_id", "")) else "")
        return f"""; File sinh tự động bởi Control Center v{APP_VERSION} - không sửa tay
[Setup]
{app_id_line}
{prev_block}AppName={cfg.product}
AppVersion={cfg.version}
AppPublisher={cfg.company}
AppCopyright={cfg.copyright}
DefaultDirName={{autopf}}\\{folder}
DefaultGroupName={cfg.product}
UninstallDisplayIcon={{app}}\\{main_exe}
OutputDir={cfg.installer_dir}
OutputBaseFilename={cfg.exe_stem}_v{cfg.version}_Setup
{icon_line}{arch_line}{comp_block}{close_apps_block}WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài Desktop"; GroupDescription: "Lối tắt:"{autostart_task_line}

[Files]
{files}
{extra_files}
{install_delete_block}
[Icons]
Name: "{{group}}\\{cfg.product}"; Filename: "{{app}}\\{main_exe}"
Name: "{{group}}\\Gỡ bỏ {cfg.product}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{cfg.product}"; Filename: "{{app}}\\{main_exe}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{main_exe}"; Description: "Khởi chạy {cfg.product} ngay"; Flags: postinstall nowait skipifsilent
{autostart_registry_block}{downgrade_code_block}"""

    def build(self, cfg: BuildConfig, artifact: str, on_line: Callable[[str], None],
              priority: str = "normal", extra_files: str = "") -> tuple[bool, str]:
        main_exe = cfg.main_exe_in(artifact)
        os.makedirs(cfg.installer_dir, exist_ok=True)
        os.makedirs(cfg.work_dir, exist_ok=True)
        iss_path = os.path.join(cfg.work_dir, f"{cfg.exe_stem}_installer.iss")
        Path(iss_path).write_text(self.render(cfg, artifact, main_exe, extra_files), encoding="utf-8-sig")
        on_line(f"> ISCC  : {self.iscc_exe}\n> Script: {iss_path}\n")
        rc = self.runner.run([self.iscc_exe, iss_path], cwd=cfg.work_dir, on_line=on_line, priority=priority)
        expected = os.path.join(cfg.installer_dir, f"{cfg.exe_stem}_v{cfg.version}_Setup.exe")
        if rc == 0 and os.path.isfile(expected):
            return True, expected
        return False, f"ISCC kết thúc với mã {rc} (chi tiết trong file log)."


# ============================================================================
#  DỊCH VỤ: ĐÓNG GÓI FILE .EXE ĐÃ BUILD SẴN (VD: Visual Studio 2022 -> Release) BẰNG INNO SETUP
# ============================================================================
@dataclass
class VsPackageConfig:
    """Cấu hình cho Tab 3: KHÔNG biên dịch mã nguồn gì cả - chỉ lấy file .exe (hoặc cả
    thư mục Release chứa .exe + các DLL phụ thuộc) mà Visual Studio 2022 đã xuất ra sau
    khi bấm Release, rồi đóng gói thành bộ cài bằng Inno Setup (ISCC.exe).

    Cố ý đặt trùng tên các thuộc tính/thuộc tính-suy-ra với BuildConfig (python.bits,
    exe_stem, work_dir, installer_dir, installer_threads, main_exe_in...) để dùng lại
    NGUYÊN VẸN InnoSetupBuilder.render()/build() mà không phải chép code sinh file .iss."""
    exe_path: str                    # file .exe HOẶC thư mục Release (vd: bin\\Release\\net8.0-windows)
    icon: str = ""                   # chỉ dùng cho SetupIconFile của bộ cài (icon trong exe do VS tự nhúng)
    company: str = "Công an xã Tri Phú"
    product: str = "Công cụ Tự động hóa Nghiệp vụ"
    version: str = "1.0.0.0"
    copyright: str = "© 2026 Mã Đức Hiển"
    iscc_path: str = ""
    installer_compression: str = "balanced"
    close_apps_on_install: bool = True
    warn_on_downgrade: bool = True
    autostart_with_windows: bool = False
    obsolete_paths: list[str] = field(default_factory=list)
    data_files: list[str] = field(default_factory=list)   # DLL/config/tài nguyên phụ trội, nếu có
    data_dirs: list[str] = field(default_factory=list)
    arch64: bool = True
    hardware: Optional[HardwareProfile] = None

    @property
    def python(self) -> PythonInfo:
        # InnoSetupBuilder.render() chỉ đọc cfg.python.bits để quyết định ArchitecturesInstallIn64BitMode
        return PythonInfo(path="", bits=64 if self.arch64 else 32)

    @property
    def exe_stem(self) -> str:
        base = Path(self.exe_path).stem if self.exe_path else "app"
        return sanitize_filename(self.product, fallback=base)

    @property
    def base_dir(self) -> str:
        if not self.exe_path:
            return str(APP_DIR)
        p = os.path.abspath(self.exe_path)
        return os.path.dirname(p) if os.path.isfile(p) else p

    @property
    def work_dir(self) -> str:
        return os.path.join(self.base_dir, "_installer_build")

    @property
    def installer_dir(self) -> str:
        return os.path.join(self.base_dir, "installer")

    @property
    def installer_threads(self) -> int:
        return installer_threads_for(self.hardware or HardwareProfile.quick(), "balanced", self.installer_compression)

    def main_exe_in(self, artifact: str) -> str:
        if os.path.isfile(artifact):
            return os.path.basename(artifact)
        exes = sorted(Path(artifact).glob("*.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
        return exes[0].name if exes else f"{self.exe_stem}.exe"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.exe_path or not os.path.exists(self.exe_path):
            errors.append("Chưa chọn file .exe (hoặc thư mục Release) hợp lệ.")
        elif os.path.isfile(self.exe_path) and not self.exe_path.lower().endswith(".exe"):
            errors.append("File đã chọn không phải file .exe.")
        elif os.path.isdir(self.exe_path) and not list(Path(self.exe_path).glob("*.exe")):
            errors.append("Thư mục đã chọn không chứa file .exe nào.")
        if not re.fullmatch(r"\d+(\.\d+){3}", self.version):
            errors.append(f"Phiên bản '{self.version}' không đúng dạng x.x.x.x.")
        if self.icon and not os.path.isfile(self.icon):
            errors.append(f"File icon không tồn tại: {self.icon}")
        if self.icon and not self.icon.lower().endswith(".ico"):
            errors.append("Icon phải là file .ico.")
        for p in self.data_files:
            if not os.path.isfile(p):
                errors.append(f"File đính kèm không tồn tại: {p}")
        for d in self.data_dirs:
            if not os.path.isdir(d):
                errors.append(f"Thư mục đính kèm không tồn tại: {d}")
        if not self.iscc_path or not os.path.isfile(self.iscc_path):
            errors.append("Chưa tìm thấy ISCC.exe (Inno Setup). Hãy chọn đường dẫn thủ công "
                           "(mặc định: E:\\Program Files\\Inno Setup 7\\ISCC.exe).")
        if self.installer_compression not in InnoSetupBuilder.COMPRESSION:
            errors.append(f"Mức nén bộ cài không hợp lệ: {self.installer_compression}")
        return errors


class BuildFailureDiagnostics:
    """Nhận diện các lỗi toolchain thường gặp và đưa ra cách sửa có thể làm ngay."""

    ZIG_CRT_MARKERS = (
        "zigc.lib", "undefined symbol: frexpf", "undefined symbol: wmemchr",
        "undefined symbol: strtok_r", "undefined symbol: __QNAN",
    )
    OOM_MARKERS = ("out of memory", "memory allocation", "c1060", "out of heap space",
                   "cc1plus: out of memory", "cc1: out of memory", "virtual memory exhausted")

    @classmethod
    def diagnose(cls, cfg: BuildConfig, output: str) -> str:
        lower = output.lower()
        script_name = os.path.basename(cfg.script)
        if cfg.compiler == "Nuitka" and any(marker.lower() in lower for marker in cls.ZIG_CRT_MARKERS):
            return (
                "[CHẨN ĐOÁN TOOLCHAIN]\n"
                "Nuitka đã biên dịch xong mã Python nhưng linker thất bại ở backend Zig/lld-link "
                "(zigc.lib thiếu các symbol CRT như frexpf, wmemchr, isnan). Đây KHÔNG phải lỗi trong "
                f"{script_name}.\n\n"
                "Cách sửa khuyến nghị cho Python 3.13 x64:\n"
                "1. Cài Visual Studio 2022 Build Tools, workload 'Desktop development with C++' + Windows SDK.\n"
                "2. Chọn Backend C/C++ = 'MSVC (khuyến nghị)' trong Control Center.\n"
                "3. Tắt LTO cho lần build kiểm tra đầu tiên.\n"
                "4. Xoá thư mục dist và build của lần lỗi rồi build lại."
            )
        if "non downloaded winlibs-gcc" in lower or ("being ignored" in lower and "gcc" in lower):
            return (
                "[CHẨN ĐOÁN TOOLCHAIN]\n"
                "Nuitka đang bỏ qua GCC MSYS2/UCRT64 vì không phải bộ WinLibs do Nuitka tải và kiểm soát. "
                "Trên Python 3.13, chọn --msvc=latest (khuyến nghị) hoặc --mingw64 kèm Python 3.12."
            )
        if any(m in lower for m in cls.OOM_MARKERS):
            return (
                "[CHẨN ĐOÁN TÀI NGUYÊN]\n"
                f"Trình biên dịch C hết bộ nhớ (đang chạy {cfg.effective_jobs} luồng song song, "
                f"LTO={'bật' if cfg.lto else 'tắt'}).\n"
                "Giảm 'Luồng biên dịch C' (vd. một nửa số lõi) hoặc chọn chế độ Cân bằng/Tiết kiệm, "
                "tắt LTO, đóng bớt ứng dụng nặng rồi build lại."
            )
        m = re.search(r"No module named (nuitka|PyInstaller)\b", output, re.I)
        if m:
            pkg = "nuitka" if m.group(1).lower() == "nuitka" else "pyinstaller"
            return (
                "[CHẨN ĐOÁN]\n"
                f"Python dùng để build CHƯA cài {m.group(1)}: {cfg.python.path}\n"
                f"Cài vào đúng Python đó: \"{cfg.python.path}\" -m pip install {pkg}\n"
                "(hoặc bấm nút 'Cài Nuitka' / 'Cài PyInstaller'), hoặc chọn python.exe khác bằng '🔧 Cấu hình Python'."
            )
        if "tk-inter" in lower and "not installed" in lower:
            return (
                "[CHẨN ĐOÁN PLUGIN tk-inter]\n"
                "Đang bật plugin tk-inter nhưng Python build không có Tcl/Tk. Nếu phần mềm KHÔNG dùng tkinter "
                "(vd giao diện PySide6/PyQt), bỏ tick 'Plugin tk-inter (Nuitka)'; nếu có dùng, cài lại Python "
                "và tick 'tcl/tk and IDLE'."
            )
        m = re.search(r"failed to locate module '?([\w.]+)'? you asked to include", output, re.I)
        if m:
            name = m.group(1).split(".")[0]
            return (
                "[CHẨN ĐOÁN THƯ VIỆN]\n"
                f"Python dùng để build KHÔNG có thư viện '{name}' mà code cần (import trong try/except).\n"
                f"Cài vào đúng Python build: \"{cfg.python.path}\" -m pip install "
                f"{ImportChecker.PIP_NAMES.get(name, name)}\n"
                "rồi build lại (hoặc bấm '🔍 Kiểm tra thư viện' ở mục 1)."
            )
        if cfg.compiler == "PyInstaller" and "lost sys.stdin" in lower:
            return (
                "[CHẨN ĐOÁN]\n"
                "PyInstaller đang hỏi y/N để ghi đè thư mục cũ. Bản này đã thêm --noconfirm; "
                "nếu vẫn lỗi hãy xoá thư mục dist/build cũ rồi build lại."
            )
        return (
            "[CHẨN ĐOÁN]\n"
            f"{cfg.compiler} thất bại ở bước backend. Hãy mở file log của lần build này (nút 'Mở log') và thử "
            "build lại với LTO tắt; nếu vẫn lỗi, chọn compiler backend khác và gửi kèm file "
            f"{os.path.basename(cfg.nuitka_report_path)} trong thư mục build."
        )


# ============================================================================
#  DỊCH VỤ 8: TIẾN ĐỘ ƯỚC LƯỢNG (có lịch sử) + NHẬT KÝ TỪNG LẦN BUILD
# ============================================================================
class ProgressTracker:
    """Ước lượng tiến độ 0-100 từ log của trình đóng gói.

    Nuitka/PyInstaller KHÔNG báo % tổng thể nên dùng MỐC theo từ khoá và cho thanh "trườn" chậm
    tới trần giữa 2 mốc. v3.1: nếu có LỊCH SỬ (BuildHistory) thì % của mỗi mốc được đặt lại theo
    thời gian thực đo được lần trước và thanh chạy theo thời gian -> đều, có ETA. Thuần Python, test được.
    """

    CREEP_PER_SEC = 0.06   # %/giây khi chưa gặp mốc mới (~3,6 %/phút)

    NUITKA = (
        (r"Starting Python compilation", 5.0, "Nuitka: phân tích & tối ưu mã Python (đơn luồng)..."),
        (r"Completed Python level compilation", 40.0, "Nuitka: xong phần Python, chuyển sang sinh mã C..."),
        (r"Generating source code for C backend", 45.0, "Nuitka: sinh mã C..."),
        (r"Running data composer", 50.0, "Nuitka: đóng gói hằng số..."),
        (r"Running C compilation via Scons", 55.0, "Nuitka: biên dịch C song song (bước lâu nhất)..."),
        (r"Backend C compiler:", 58.0, "Nuitka: đang biên dịch C..."),
        (r"Backend C linking", 82.0, "Nuitka: liên kết (link) file thực thi..."),
        (r"Nuitka-Onefile:", 88.0, "Nuitka: đóng gói onefile..."),
        (r"Successfully created|Keeping build directory", 90.0, "Nuitka: hoàn tất biên dịch."),
    )
    PYINSTALLER = (
        (r"PyInstaller: \d", 5.0, "PyInstaller: khởi động..."),
        (r"INFO: Analyzing", 12.0, "PyInstaller: phân tích import..."),
        (r"Processing module hooks", 30.0, "PyInstaller: xử lý hook..."),
        (r"Looking for dynamic libraries", 45.0, "PyInstaller: tìm DLL phụ thuộc..."),
        (r"Building PYZ", 60.0, "PyInstaller: đóng gói PYZ..."),
        (r"Building PKG", 70.0, "PyInstaller: đóng gói PKG..."),
        (r"Building EXE", 80.0, "PyInstaller: tạo EXE..."),
        (r"Building COLLECT", 87.0, "PyInstaller: gom thư mục onedir..."),
        (r"Build complete|completed successfully", 90.0, "PyInstaller: hoàn tất."),
    )
    INSTALLER = (
        (r"Successful compile", 99.5, "Inno Setup: nén xong, đang ghi Setup.exe..."),
    )

    def __init__(self, compiler: str, expected: Optional[dict] = None):
        table = self.NUITKA if compiler == "Nuitka" else self.PYINSTALLER
        self._build = [(re.compile(p, re.I), pct, lbl) for p, pct, lbl in table]
        self._installer = [(re.compile(p, re.I), pct, lbl) for p, pct, lbl in self.INSTALLER]
        self.phase = "build"      # build | installer
        self.value = 0.0
        self.cap = 5.0
        self.label = "Chuẩn bị..."
        self.marks: dict[str, float] = {}          # nhãn mốc -> giây kể từ lúc bắt đầu (ghi vào lịch sử)
        self.expected_total: Optional[float] = None
        if expected and expected.get("total"):
            self.expected_total = float(expected["total"])
            self._retime(expected.get("marks") or {}, float(expected.get("marks_total") or expected["total"]))

    def _retime(self, marks: dict, total: float) -> None:
        """Đặt lại % từng mốc theo THỜI GIAN đo được ở lần build trước -> thanh chạy đều, không giật."""
        if total <= 0 or not marks:
            return
        retimed = []
        last = 0.0
        for rx, pct, lbl in self._build:
            t = marks.get(lbl)
            if isinstance(t, (int, float)) and t >= 0:
                pct = 4.0 + 86.0 * min(1.0, float(t) / total)
            pct = min(90.0, max(pct, last + 0.5))
            last = pct
            retimed.append((rx, pct, lbl))
        self._build = retimed

    def set_stage(self, value: float, cap: float, label: str, phase: Optional[str] = None) -> None:
        self.value = max(self.value, float(value))
        self.cap = max(float(cap), self.value)
        self.label = label
        if phase:
            self.phase = phase

    def observe(self, line: str, elapsed: float = 0.0) -> bool:
        """Đọc 1 dòng log; trả True nếu tiến độ/nhãn thay đổi."""
        table = self._installer if self.phase == "installer" else self._build
        changed = False
        for rx, pct, lbl in table:
            if not rx.search(line):
                continue
            if lbl not in self.marks:
                self.marks[lbl] = round(elapsed, 1)
            self.label = lbl
            later = [p for _, p, _ in table if p > pct]
            self.cap = max((min(later) - 1.0) if later else min(pct + 3.0, 99.0), self.value)
            if pct > self.value:
                self.value = pct
            changed = True
        if self.phase == "installer" and "Compressing" in line:
            self.value = min(self.cap, self.value + 0.05)
            changed = True
        return changed

    def tick(self, dt: float, elapsed: float = 0.0) -> float:
        """Gọi định kỳ từ UI: theo thời gian thực (nếu có lịch sử) và trườn chậm tới trần khi log im lặng."""
        if self.value < self.cap:
            if self.expected_total and self.phase == "build":
                target = 100.0 * elapsed / self.expected_total * 0.97
                self.value = max(self.value, min(target, self.cap))
            self.value = min(self.cap, self.value + self.CREEP_PER_SEC * dt)
        return self.value

    def eta(self, elapsed: float) -> Optional[float]:
        if not self.expected_total:
            return None
        return self.expected_total - elapsed

    def finish(self, ok: bool) -> None:
        if ok:
            self.value = self.cap = 100.0


class BuildLogWriter:
    """Mỗi lần build ghi MỘT file log đầy đủ vào <thư mục dự án>\\build_logs\\build_<exe>_<thời gian>.log."""

    KEEP = 30

    def __init__(self, cfg: BuildConfig):
        self.path = ""
        self._fh = None
        self._lock = threading.Lock()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"build_{cfg.exe_stem}_{stamp}.log"
        for folder in (cfg.log_dir, str(APP_DIR / "build_logs")):
            try:
                os.makedirs(folder, exist_ok=True)
                candidate = os.path.join(folder, name)
                self._fh = open(candidate, "w", encoding="utf-8", buffering=1)
                self.path = candidate
                break
            except OSError as exc:
                log.warning("Không tạo được log tại %s: %s", folder, exc)
        if self.path:
            self.prune(os.path.dirname(self.path), self.KEEP)

    @staticmethod
    def prune(folder: str, keep: int) -> None:
        try:
            files = sorted(Path(folder).glob("build_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[keep:]:
                old.unlink(missing_ok=True)
        except OSError:
            pass

    def write(self, text: str) -> None:
        if self._fh is None:
            return
        with self._lock:
            try:
                self._fh.write(text)
            except (OSError, ValueError):
                pass

    def note(self, text: str) -> None:
        self.write(f"[{datetime.now():%H:%M:%S}] {text.rstrip()}\n")

    def header(self, cfg: BuildConfig, cmd: list[str]) -> None:
        tool = (f"{cfg.compiler} {cfg.python.nuitka}  backend={cfg.nuitka_backend}" if cfg.compiler == "Nuitka"
                else f"{cfg.compiler} {cfg.python.pyinstaller}")
        hw = cfg.hardware.summary() if cfg.hardware else "(chưa dò)"
        lines = [
            "=" * 78,
            f" CONTROL CENTER v{APP_VERSION} TURBO - NHẬT KÝ ĐÓNG GÓI",
            f" Bắt đầu    : {datetime.now():%Y-%m-%d %H:%M:%S}",
            f" Script     : {os.path.abspath(cfg.script)}",
            f" Python     : {cfg.python.version} ({cfg.python.bits}-bit)  {cfg.python.path}",
            f" Trình build: {tool}",
            f" Chế độ     : {cfg.build_mode} | {cfg.console_mode} | UAC={'có' if cfg.uac_admin else 'không'}"
            f" | LTO={'bật' if cfg.lto else 'tắt'} | tk-inter={'bật' if cfg.tk_plugin else 'tắt'}"
            f" | xoá build/cache={'có' if cfg.clean_build else 'không (tăng dần)'}",
            f" Hiệu năng  : mode={cfg.perf_mode} | jobs={cfg.effective_jobs} | ưu tiên={PRIORITY_LABELS[cfg.priority_class]}"
            f" | chặn ngủ={'có' if cfg.keep_awake else 'không'} | power plan={'có' if cfg.power_plan else 'không'}"
            f" | nén onefile={'có' if cfg.onefile_compress else 'không'} | slim imports={'có' if cfg.slim_imports else 'không'}"
            f" | no_docstrings={'có' if cfg.no_docstrings else 'không'}",
            f" Máy        : {hw}",
            f" Metadata   : {cfg.product} | {cfg.company} | v{cfg.version} | {cfg.copyright} | exe={cfg.exe_stem}.exe",
            f" Icon       : {cfg.icon or '(không)'}",
            f" Dữ liệu    : {len(cfg.data_files)} file, {len(cfg.data_dirs)} thư mục",
            f" Đầu ra     : dist={cfg.output_dir}",
            f"              work={cfg.work_dir}",
            f" Inno Setup : {'có' if cfg.make_installer else 'không'}  ISCC={cfg.iscc_path or '(tự dò)'}"
            f"  nén={cfg.installer_compression} x {cfg.installer_threads} luồng",
            f" Lệnh       : {subprocess.list2cmdline(cmd)}",
            "=" * 78,
            "",
        ]
        self.write("\n".join(lines))

    def footer(self, ok: bool, message: str, elapsed: float) -> None:
        self.write("\n" + "=" * 78 + "\n")
        self.write(f" KẾT QUẢ    : {'THÀNH CÔNG' if ok else 'THẤT BẠI'}\n")
        self.write(f" Thông điệp : {message}\n")
        self.write(f" Thời gian  : {fmt_elapsed(elapsed)}  (kết thúc {datetime.now():%Y-%m-%d %H:%M:%S})\n")
        self.write("=" * 78 + "\n")

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.close()
                except OSError:
                    pass
                self._fh = None


# ============================================================================
#  DỊCH VỤ 9: CHUỖI BUILD HOÀN CHỈNH (chạy trọn vẹn trong thread nền, có tinh chỉnh hệ thống)
# ============================================================================
class BuildPipeline:
    """Sự kiện gửi về UI (qua emit):
         ("logfile", path)                      - đường dẫn file log của lần build này
         ("tips", [str, ...])                   - gợi ý hiệu năng cho lần build này
         ("stage", (value, cap, label, phase))  - mốc tiến độ tường minh
         ("line", text)                         - 1 dòng output
         ("diagnosis", text)                    - chẩn đoán khi thất bại
         ("done", (ok, message, elapsed, path)) - kết thúc
    """

    def __init__(self, cfg: BuildConfig, emit: Callable[[str, object], None]):
        self.cfg = cfg
        self.emit = emit
        self.runner = ProcessRunner()
        self.cancelled = threading.Event()
        self.logger: Optional[BuildLogWriter] = None
        self._t0 = time.monotonic()

    def cancel(self) -> None:
        self.cancelled.set()
        self.runner.terminate()

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:  # noqa: BLE001
            log.exception("Build pipeline lỗi")
            self._finish(False, f"Lỗi không mong đợi: {exc}")

    def _say(self, text: str) -> None:
        if self.logger:
            self.logger.note(text)
        self.emit("line", text if text.endswith("\n") else text + "\n")

    def _stage(self, value: float, cap: float, label: str, phase: str = "build") -> None:
        if self.logger:
            self.logger.note(f"=== {label}")
        self.emit("stage", (value, cap, label, phase))

    def _finish(self, ok: bool, message: str) -> None:
        elapsed = time.monotonic() - self._t0
        path = ""
        if self.logger:
            self.logger.footer(ok, message, elapsed)
            self.logger.close()
            path = self.logger.path
        self.emit("done", (ok, message, elapsed, path))

    def _run(self) -> None:
        cfg = self.cfg
        os.makedirs(cfg.output_dir, exist_ok=True)
        os.makedirs(cfg.work_dir, exist_ok=True)
        if cfg.hardware is None:
            cfg.hardware = HardwareProfile.probe(cfg.script_dir)   # nhanh (không gọi PowerShell)
        cmd = BuildCommandFactory.create(cfg)
        self.logger = BuildLogWriter(cfg)
        self.logger.header(cfg, cmd)
        self.emit("logfile", self.logger.path)
        if cfg.compiler == "Nuitka":
            already = {"tk-inter"} if cfg.tk_plugin else set()
            detected = DependencyScanner.describe_detected(cfg.script, already)
            if detected:
                self._say("> [TỰ ĐỘNG] Phát hiện thư viện cần cờ riêng, đã tự thêm vào lệnh build:")
                for line in detected:
                    self._say(f">   - {line}")
        if cfg.import_report is not None:
            self._say("> [KIỂM TRA THƯ VIỆN] Kết quả trước khi build:")
            for line in cfg.import_report.summary_lines():
                self._say(f">   {line}")
        elif not cfg.verify_imports:
            self._say("> [KIỂM TRA THƯ VIỆN] ĐÃ TẮT - exe có thể thiếu thư viện mà không báo lỗi.")
        if cfg.make_installer:
            self._say(f"> [MÃ SẢN PHẨM] {cfg.product_id or '(chưa có - AppId sinh từ tên phần mềm)'}"
                      f"  ->  AppId {{{InnoSetupBuilder.app_id_for(cfg)}}}")
        if cfg.make_installer and cfg.uninstall_old_versions:
            exes, prefixes = InnoSetupBuilder.old_version_rules(cfg, f"{cfg.exe_stem}.exe")
            self._say("> [GỠ BẢN CŨ] Bộ cài sẽ tự gỡ sạch mọi bản đã cài có exe: " + ", ".join(exes)
                      + (" | hoặc tên bắt đầu bằng: " + ", ".join(prefixes) if prefixes else "")
                      + (" | xoá cả thư mục cũ còn sót" if cfg.delete_old_dirs else ""))
        tips = PerformanceAdvisor.tips(cfg.hardware, cfg.perf_context())
        for tip in tips:
            self._say(f"> [GỢI Ý] {tip}")
        self.emit("tips", tips)

        tuner = SystemTuner(cfg.keep_awake, cfg.power_plan, self._say)
        tuner.enter()
        try:
            ok, message = self._execute(cmd)
        finally:
            tuner.exit()
        self._finish(ok, message)

    def _execute(self, cmd: list[str]) -> tuple[bool, str]:
        cfg = self.cfg
        self._stage(2.0, 8.0, f"Bước 1/3 - Biên dịch bằng {cfg.compiler} "
                              f"({cfg.effective_jobs} luồng C, ưu tiên {PRIORITY_LABELS[cfg.priority_class]})...")
        if cfg.compiler == "Nuitka":
            backend = cfg.nuitka_backend.upper() if cfg.nuitka_backend != "auto" else "TỰ ĐỘNG"
            self._say(f"> Backend C/C++: {backend}  |  --jobs={cfg.effective_jobs}  |  LTO={'bật' if cfg.lto else 'tắt'}")
            if cfg.nuitka_backend == "mingw64" and NuitkaToolchain.python_major_minor(cfg.python) >= (3, 13):
                self._say("> CẢNH BÁO: MinGW64 + Python 3.13+ là experimental; nếu lỗi, chuyển sang MSVC.")
        self._say("> Lệnh: " + subprocess.list2cmdline(cmd))
        build_lines: list[str] = []

        def on_build_line(line: str) -> None:
            build_lines.append(line)
            if self.logger:
                self.logger.write(line)
            self.emit("line", line)

        rc = self.runner.run(cmd, cwd=cfg.script_dir, on_line=on_build_line, priority=cfg.priority_class)
        if self.cancelled.is_set():
            return False, "Đã dừng theo yêu cầu người dùng."
        if rc != 0:
            diagnosis = BuildFailureDiagnostics.diagnose(cfg, "".join(build_lines[-400:]))
            if self.logger:
                self.logger.write("\n" + diagnosis + "\n")
            self.emit("diagnosis", diagnosis)
            return False, f"{cfg.compiler} kết thúc với mã lỗi {rc}."

        self._stage(92.0, 93.0, "Bước 2/3 - Xác định thành phẩm...")
        artifact = cfg.locate_artifact()
        if not artifact:
            return False, f"Build báo thành công nhưng không thấy thành phẩm trong {cfg.output_dir}"
        self._say(f"[OK] Thành phẩm: {artifact}")

        if cfg.verify_imports:
            ok_mods, missing_mods, note = BuildVerifier.verify(cfg)
            if note:
                self._say(f"> [KIỂM TRA THÀNH PHẨM] {note}")
            if ok_mods:
                self._say("> [KIỂM TRA THÀNH PHẨM] Đã có trong exe: " + ", ".join(ok_mods))
            if missing_mods:
                diagnosis = (
                    "[CHẨN ĐOÁN THƯ VIỆN]\n"
                    f"Exe vừa build THIẾU thư viện: {', '.join(missing_mods)}.\n"
                    "Code có import các thư viện này nhưng trình đóng gói đã không gói chúng vào "
                    "(thường do import nằm trong try/except nên lỗi bị nuốt). Nếu phát hành, phần "
                    "mềm sẽ chạy THIẾU tính năng (vd thiếu pystray -> mất icon khay hệ thống).\n\n"
                    "Cách sửa:\n"
                    f"1. Kiểm tra lại trong đúng Python build: {cfg.python.path}\n"
                    "2. Bấm '🔍 Kiểm tra thư viện' ở mục 1, cài gói còn thiếu rồi build lại.\n"
                    "3. Nếu cố ý không gói, thêm --nofollow-import-to=<tên> ở mục 5."
                )
                if self.logger:
                    self.logger.write("\n" + diagnosis + "\n")
                self.emit("diagnosis", diagnosis)
                return False, ("Exe build xong nhưng THIẾU thư viện " + ", ".join(missing_mods)
                               + " -> KHÔNG tạo bộ cài để tránh phát hành bản lỗi.")

        if not cfg.make_installer:
            self._stage(99.0, 100.0, "Hoàn tất (không tạo bộ cài).")
            return True, f"Hoàn tất. Thành phẩm: {artifact}"

        comp_label = InnoSetupBuilder.COMPRESSION.get(cfg.installer_compression, "lzma2/normal")
        self._stage(95.0, 99.0, f"Bước 3/3 - Tạo bộ cài Inno Setup ({comp_label}, {cfg.installer_threads} luồng)...",
                    phase="installer")
        iscc = IsccLocator.find(cfg.iscc_path)
        if not iscc:
            return True, "Build xong nhưng KHÔNG tìm thấy ISCC.exe nên bỏ qua bước tạo bộ cài."

        def on_iscc_line(line: str) -> None:
            if self.logger:
                self.logger.write(line)
            self.emit("line", line)

        ok, msg = InnoSetupBuilder(iscc, self.runner).build(cfg, artifact, on_line=on_iscc_line,
                                                            priority=cfg.priority_class)
        if self.cancelled.is_set():
            return False, "Đã dừng khi đang tạo bộ cài."
        if ok:
            return True, f"Đã tạo bộ cài: {msg}"
        return False, f"Inno Setup thất bại: {msg}"


# ============================================================================
#  GIAO DIỆN - THÀNH PHẦN DÙNG CHUNG
# ============================================================================
class Palette:
    BLUE = "#2563eb"
    GREEN = "#16a34a"
    AMBER = "#f59e0b"
    RED = "#dc2626"
    GRAY = "#9ca3af"
    SLATE = "#475569"


def color_button(master: tk.Misc, text: str, color: str, command: Callable[[], None], **kw) -> tk.Button:
    return tk.Button(
        master, text=text, bg=color, fg="white", activebackground=color, activeforeground="white",
        relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), padx=10, pady=4, command=command, **kw,
    )


class MainThreadDispatcher:
    """Thread nền gọi dispatcher.call(fn, ...) -> fn được chạy trên luồng UI. Tk KHÔNG an toàn luồng."""

    def __init__(self, root: tk.Tk, interval_ms: int = 40):
        self.root = root
        self.queue: "queue.Queue[tuple[Callable, tuple, dict]]" = queue.Queue()
        self.interval = interval_ms
        self._pump()

    def call(self, fn: Callable, *args, **kwargs) -> None:
        self.queue.put((fn, args, kwargs))

    def _pump(self) -> None:
        try:
            for _ in range(500):
                fn, args, kwargs = self.queue.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception:  # noqa: BLE001
                    log.exception("Lỗi trong callback UI")
        except queue.Empty:
            pass
        try:
            self.root.after(self.interval, self._pump)
        except tk.TclError:
            pass


class ConsoleText(ttk.Frame):
    """Text + scrollbar, ghi theo lô (batch) mỗi 60ms, có màu theo tag, tự cắt bớt khi quá dài."""

    MAX_LINES = 6000

    def __init__(self, master: tk.Misc, bg: str, fg: str, height: Optional[int] = None):
        super().__init__(master)
        extra = {"height": height} if height else {}
        self.text = tk.Text(self, wrap="word", font=("Consolas", 10), bg=bg, fg=fg,
                            insertbackground=fg, relief="flat", padx=6, pady=4, undo=False, **extra)
        sb = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for tag, color in (("info", "#3b82f6"), ("ok", "#16a34a"), ("warn", "#d97706"),
                           ("err", "#ef4444"), ("ai", "#a855f7")):
            self.text.tag_configure(tag, foreground=color)
        self._pending: list[tuple[str, Optional[str]]] = []
        self._scheduled = False

    def append(self, text: str, tag: Optional[str] = None) -> None:
        self._pending.append((text, tag))
        if not self._scheduled:
            self._scheduled = True
            self.after(60, self._flush)

    def _flush(self) -> None:
        self._scheduled = False
        pending, self._pending = self._pending, []
        for text, tag in pending:
            if tag:
                self.text.insert("end", text, tag)
            else:
                self.text.insert("end", text)
        total = int(self.text.index("end-1c").split(".")[0])
        if total > self.MAX_LINES:
            self.text.delete("1.0", f"{total - self.MAX_LINES}.0")
        self.text.see("end")

    def clear(self) -> None:
        self._pending.clear()
        self.text.delete("1.0", "end")

    def content(self) -> str:
        return self.text.get("1.0", "end-1c")


class ScrollableFrame(ttk.Frame):
    """Khung cuộn dọc cho form dài: đặt widget vào .inner; cuộn bằng thanh trượt hoặc lăn chuột."""

    def __init__(self, master: tk.Misc, **kw):
        super().__init__(master, **kw)
        bg = ttk.Style(self).lookup("TFrame", "background") or "#f0f0f0"
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, bg=bg, yscrollincrement=24)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")

    def _pointer_inside(self, event: tk.Event) -> bool:
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return False
        while w is not None:
            if w is self.canvas:
                return True
            w = getattr(w, "master", None)
        return False

    def _on_wheel(self, event: tk.Event) -> None:
        if not self._pointer_inside(event):
            return
        if isinstance(event.widget, (tk.Listbox, tk.Text)):
            return
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= self.canvas.winfo_height():
            return
        num = getattr(event, "num", None)
        if num == 4:
            steps = -3
        elif num == 5:
            steps = 3
        else:
            steps = -3 if event.delta > 0 else 3
        self.canvas.yview_scroll(steps, "units")

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0)


# ============================================================================
#  TAB 1: PHÂN TÍCH LOG & AI
# ============================================================================
class AnalyzerTab(ttk.Frame):
    IDLE_TEXT = "⚡ Phân Tích & Đọc Lỗi"

    def __init__(self, master: tk.Misc, app: "ControlCenterApp"):
        super().__init__(master, padding=12)
        self.app = app
        s = app.settings
        self.folder_var = tk.StringVar(value=s.last_log_folder)
        self.password_var = tk.StringVar(value=s.effective_zip_password)
        self.remember_pw_var = tk.BooleanVar(value=s.remember_password)
        self.url_var = tk.StringVar(value=s.ollama_url)
        self.model_var = tk.StringVar(value=s.ollama_model)
        self.use_ai_var = tk.BooleanVar(value=True)
        self.cancel_event = threading.Event()
        self.running = False
        self._build_ui()
        self.console.append("[HỆ THỐNG] Sẵn sàng giải mã CrashReport (.zip).\n", "info")
        if not HAS_PYZIPPER:
            self.console.append("[CẢNH BÁO] Chưa cài pyzipper -> chỉ đọc được zip KHÔNG mã hoá AES. "
                                "Chạy: pip install pyzipper\n", "warn")

    def _build_ui(self) -> None:
        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        ttk.Label(row1, text="Thư mục log:", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Entry(row1, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=8)
        color_button(row1, "📁 Chọn thư mục", Palette.BLUE, self._choose_folder).pack(side="left")

        row2 = ttk.Frame(self)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Mật khẩu zip:").pack(side="left")
        self.pw_entry = ttk.Entry(row2, textvariable=self.password_var, show="•", width=16)
        self.pw_entry.pack(side="left", padx=(6, 2))
        ttk.Button(row2, text="👁", width=3, command=self._toggle_password).pack(side="left")
        ttk.Checkbutton(row2, text="Ghi nhớ", variable=self.remember_pw_var).pack(side="left", padx=(4, 16))
        ttk.Checkbutton(row2, text="Nhờ AI (Ollama) đề xuất", variable=self.use_ai_var).pack(side="left")
        ttk.Label(row2, text="Model:").pack(side="left", padx=(12, 4))
        self.model_box = ttk.Combobox(row2, textvariable=self.model_var, width=22)
        self.model_box.pack(side="left")
        ttk.Button(row2, text="↻", width=3, command=self._refresh_models).pack(side="left", padx=(2, 12))
        ttk.Label(row2, text="URL:").pack(side="left")
        ttk.Entry(row2, textvariable=self.url_var, width=24).pack(side="left", padx=4)

        row3 = ttk.Frame(self)
        row3.pack(fill="x", pady=8)
        self.btn_run = color_button(row3, self.IDLE_TEXT, Palette.GREEN, self._start)
        self.btn_run.pack(side="left")
        self.btn_stop = color_button(row3, "⛔ Dừng", Palette.RED, self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=8)
        color_button(row3, "📋 Copy", Palette.AMBER, self._copy).pack(side="left")
        color_button(row3, "💾 Lưu báo cáo", Palette.SLATE, self._save_report).pack(side="left", padx=8)
        color_button(row3, "🧹 Xoá màn hình", Palette.GRAY, lambda: self.console.clear()).pack(side="left")

        box = ttk.LabelFrame(self, text="Kết quả tổng hợp (đã giải mã AES)", padding=6)
        box.pack(fill="both", expand=True)
        self.console = ConsoleText(box, bg="#f8fafc", fg="#334155")
        self.console.pack(fill="both", expand=True)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Chọn thư mục chứa file Log (.zip)",
                                         initialdir=self.folder_var.get() or None, parent=self)
        if folder:
            self.folder_var.set(folder)
            self.console.append(f"\n[HỆ THỐNG] Đã chọn thư mục: {folder}\n", "info")

    def _toggle_password(self) -> None:
        self.pw_entry.configure(show="" if self.pw_entry.cget("show") else "•")

    def _refresh_models(self) -> None:
        client = OllamaClient(self.url_var.get(), self.model_var.get())

        def worker() -> None:
            try:
                models = client.list_models()
                self.app.dispatch(self._apply_models, models)
            except OllamaError as exc:
                self.app.dispatch(self.console.append, f"[AI] {exc}\n", "warn")

        threading.Thread(target=worker, daemon=True, name="ollama-tags").start()

    def _apply_models(self, models: list[str]) -> None:
        self.model_box["values"] = models
        if models and self.model_var.get() not in models:
            self.model_var.set(models[0])
        self.console.append(f"[AI] Model khả dụng: {', '.join(models) or '(không có)'}\n", "info")

    def _set_running(self, running: bool) -> None:
        self.running = running
        if running:
            self.btn_run.config(state="disabled", text="⏳ Đang xử lý...", bg=Palette.GRAY)
            self.btn_stop.config(state="normal")
        else:
            self.btn_run.config(state="normal", text=self.IDLE_TEXT, bg=Palette.GREEN)
            self.btn_stop.config(state="disabled")

    def _start(self) -> None:
        if self.running:
            return
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Thiếu thư mục", "Vui lòng chọn thư mục chứa file log (.zip) trước!", parent=self)
            return
        password = self.password_var.get()
        if not password and not messagebox.askyesno(
                "Không có mật khẩu", "Chưa nhập mật khẩu zip. Tiếp tục thử mở như zip không mã hoá?", parent=self):
            return
        self.app.settings.last_log_folder = folder
        self.cancel_event.clear()
        self._set_running(True)
        self.console.append(f"\n{'=' * 60}\n[TIẾN TRÌNH] Quét thư mục: {folder}\n", "info")
        analyzer = LogAnalyzer(password)
        client = OllamaClient(self.url_var.get(), self.model_var.get()) if self.use_ai_var.get() else None
        threading.Thread(target=self._worker, args=(analyzer, folder, client), daemon=True, name="analyzer").start()

    def _stop(self) -> None:
        self.cancel_event.set()
        self.console.append("\n[HỆ THỐNG] Đang dừng...\n", "warn")

    def _worker(self, analyzer: LogAnalyzer, folder: str, client: Optional[OllamaClient]) -> None:
        ui = self.app.dispatch

        def report(msg: str, tag: Optional[str]) -> None:
            ui(self.console.append, msg if msg.endswith("\n") else msg + "\n", tag)

        try:
            records = analyzer.analyze(folder, report, self.cancel_event)
            groups = LogAnalyzer.group(records)
            ui(self._show_summary, groups, len(records))
            if client and groups and not self.cancel_event.is_set():
                self._ask_ai(client, groups)
        except Exception as exc:  # noqa: BLE001
            log.exception("Lỗi phân tích log")
            ui(self.console.append, f"[LỖI] {exc}\n", "err")
        finally:
            ui(self._set_running, False)

    def _show_summary(self, groups: dict[str, list[ErrorRecord]], total: int) -> None:
        self.console.append(f"{'=' * 60}\n[HOÀN TẤT] {total} file lỗi, {len(groups)} nhóm lỗi khác nhau.\n", "ok")
        for i, (sig, recs) in enumerate(groups.items(), 1):
            self.console.append(f"  #{i}: {len(recs)} máy  |  {sig[:140]}\n", "warn")

    def _ask_ai(self, client: OllamaClient, groups: dict[str, list[ErrorRecord]]) -> None:
        ui = self.app.dispatch
        ui(self.console.append, f"\n[AI] Đang nhờ {client.model} tại {client.base_url} phân tích (streaming)...\n", "ai")
        ui(self.console.append, f"\n{'*' * 20} ĐỀ XUẤT CỦA AI {'*' * 20}\n", "ai")
        try:
            client.generate_stream(LogAnalyzer.build_prompt(groups),
                                   on_token=lambda t: ui(self.console.append, t, None),
                                   cancel=self.cancel_event)
            ui(self.console.append, f"\n{'*' * 60}\n", "ai")
        except OllamaError as exc:
            ui(self.console.append, f"\n[LỖI AI] {exc}\n", "err")

    def _copy(self) -> None:
        content = self.console.content().strip()
        if not content:
            messagebox.showwarning("Trống", "Không có nội dung nào để sao chép!", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Đã sao chép", "Đã sao chép toàn bộ nội dung phân tích vào clipboard.", parent=self)

    def _save_report(self) -> None:
        path = filedialog.asksaveasfilename(title="Lưu báo cáo", defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")], parent=self)
        if path:
            Path(path).write_text(self.console.content(), encoding="utf-8")
            self.console.append(f"[HỆ THỐNG] Đã lưu báo cáo: {path}\n", "ok")

    def write_settings(self, s: AppConfig) -> None:
        s.last_log_folder = self.folder_var.get().strip()
        s.ollama_url = self.url_var.get().strip() or s.ollama_url
        s.ollama_model = self.model_var.get().strip() or s.ollama_model
        s.remember_password = self.remember_pw_var.get()
        s.zip_password = self.password_var.get() if s.remember_password else ""


# ============================================================================
#  TAB 2: ĐÓNG GÓI (UNIVERSAL BUILDER) - banner / vùng cuộn / thanh ghim đáy + BỘ TĂNG TỐC
# ============================================================================
class BuilderTab(ttk.Frame):
    IDLE_TEXT = "🚀 BẮT ĐẦU ĐÓNG GÓI TỰ ĐỘNG"
    BACKEND_LABELS = {
        "msvc": "MSVC (khuyến nghị Python 3.13)",
        "auto": "Tự động (Nuitka tự chọn)",
        "zig": "Zig (x64, phương án phụ)",
        "mingw64": "MinGW64 (experimental với Python 3.13+)",
        "clangcl": "ClangCL (cần Visual Studio)",
    }
    COMPRESSION_LABELS = InnoSetupBuilder.COMPRESSION_LABELS
    STATUS_COLORS = {"info": "#334155", "ok": "#15803d", "warn": "#b45309", "err": "#b91c1c"}

    def __init__(self, master: tk.Misc, app: "ControlCenterApp"):
        super().__init__(master, padding=(12, 10, 12, 8))
        self.app = app
        s = app.settings
        self.locator = PythonLocator(s)
        self.py_info: Optional[PythonInfo] = None
        self.pipeline: Optional[BuildPipeline] = None
        self.tool_busy = False
        self.progress: Optional[ProgressTracker] = None
        self.last_log_path = ""
        self.details_visible = bool(s.details_expanded)
        self.hw: Optional[HardwareProfile] = None
        self._probing_hw = False
        self._t0 = 0.0
        self._tick_job: Optional[str] = None
        self._status_job: Optional[str] = None
        self._tips_job: Optional[str] = None
        self._last_line = ""
        self._last_diagnosis = ""
        self.data_items: list[tuple[str, str]] = [("file", p) for p in s.data_files] + [("dir", p) for p in s.data_dirs]

        self.script_var = tk.StringVar(value=s.last_script)
        self.icon_var = tk.StringVar(value=s.icon)
        self.compiler_var = tk.StringVar(value=s.compiler)
        self.backend_var = tk.StringVar(value=self.BACKEND_LABELS.get(s.nuitka_backend, self.BACKEND_LABELS["msvc"]))
        self.build_mode_var = tk.StringVar(value=s.build_mode)
        self.console_mode_var = tk.StringVar(value=s.console_mode)
        self.uac_var = tk.BooleanVar(value=s.uac_admin)
        self.clean_var = tk.BooleanVar(value=s.clean_build)
        self.lto_var = tk.BooleanVar(value=s.lto)
        self.tk_plugin_var = tk.BooleanVar(value=s.tk_plugin)
        self.installer_var = tk.BooleanVar(value=s.make_installer)
        self.open_done_var = tk.BooleanVar(value=s.open_when_done)
        self.iscc_var = tk.StringVar(value=s.iscc_path)
        self.close_apps_var = tk.BooleanVar(value=s.close_apps_on_install)
        self.warn_downgrade_var = tk.BooleanVar(value=s.warn_on_downgrade)
        self.autostart_var = tk.BooleanVar(value=s.autostart_with_windows)
        self.verify_var = tk.BooleanVar(value=s.verify_imports)
        self.uninstall_old_var = tk.BooleanVar(value=s.uninstall_old_versions)
        self.delete_old_dirs_var = tk.BooleanVar(value=s.delete_old_dirs)
        self.old_names_text: Optional[tk.Text] = None
        self._old_names_initial = list(s.old_version_names)
        self.product_id_var = tk.StringVar(value="")
        self.product_id_hint_var = tk.StringVar(value="")
        self.src_version_var = tk.StringVar(value="")
        self.imports_var = tk.StringVar(value="Thư viện: chưa kiểm tra (tự kiểm tra khi chọn file và trước mỗi lần build).")
        self._checking_imports = False
        self._import_waiters: list[Callable[[ImportReport], None]] = []
        self.obsolete_paths_text: Optional[tk.Text] = None  # gán ở _build_ui, đọc/ghi trực tiếp
        self._obsolete_paths_initial = list(s.obsolete_paths)
        self.company_var = tk.StringVar(value=s.company)
        self.product_var = tk.StringVar(value=s.product)
        self.exe_name_var = tk.StringVar(value=s.exe_name)
        self.version_var = tk.StringVar(value=s.version)
        self.copyright_var = tk.StringVar(value=s.copyright)
        self.extra_var = tk.StringVar(value=s.extra_args)
        # TURBO
        self.perf_mode_var = tk.StringVar(value=s.perf_mode if s.perf_mode in ("turbo", "balanced", "eco") else "turbo")
        self.jobs_var = tk.StringVar(value=str(s.jobs or 0))
        self.priority_var = tk.BooleanVar(value=s.high_priority)
        self.keep_awake_var = tk.BooleanVar(value=s.keep_awake)
        self.power_plan_var = tk.BooleanVar(value=s.power_plan)
        self.onefile_compress_var = tk.BooleanVar(value=s.onefile_compress)
        self.slim_var = tk.BooleanVar(value=s.slim_imports)
        self.nodoc_var = tk.BooleanVar(value=s.no_docstrings)
        self.comp_label_var = tk.StringVar(
            value=self.COMPRESSION_LABELS.get(s.installer_compression, self.COMPRESSION_LABELS["balanced"]))
        self.hw_var = tk.StringVar(value="⏳ đang quét phần cứng...")
        self.tips_var = tk.StringVar(value="")
        self.jobs_hint_var = tk.StringVar(value="0 = tự động")
        self.comp_hint_var = tk.StringVar(value="")
        self.tools_var = tk.StringVar(value="⏳ Đang dò Python và các công cụ đóng gói ở chế độ nền...")
        self.status_var = tk.StringVar(value="Sẵn sàng. Chọn file .py, kiểm tra cấu hình rồi bấm nút đỏ.")
        self.style = ttk.Style(self)

        self._build_ui()
        # Tương thích ngược: nếu trước đây đã chọn icon nhưng chưa được thêm vào tài nguyên
        # đính kèm (bản cũ chưa có bước này) -> tự bổ sung ngay, để lần build tới có icon khay hệ thống.
        if s.icon and os.path.isfile(s.icon):
            self._ensure_icon_bundled(s.icon)
        self._refresh_data_list()
        self._load_product_id()
        self._load_source_version()
        self.console.append("> Trạng thái: Sẵn sàng.\n", "ok")
        for var in (self.compiler_var, self.backend_var, self.build_mode_var, self.lto_var, self.clean_var,
                    self.perf_mode_var, self.jobs_var, self.onefile_compress_var, self.comp_label_var,
                    self.installer_var, self.power_plan_var, self.priority_var):
            var.trace_add("write", lambda *_a: self._schedule_tips())
        custom_iscc = self.iscc_var.get()
        threading.Thread(target=self._detect_tools, args=(custom_iscc,), daemon=True, name="detect-tools").start()
        self._probe_hardware()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.banner = tk.Label(self, textvariable=self.tools_var, fg="white", bg=Palette.SLATE,
                               font=("Segoe UI", 9, "bold"), anchor="w", justify="left", padx=8, pady=4)
        self.banner.grid(row=0, column=0, sticky="ew")
        self.banner.bind("<Configure>", lambda e: self.banner.configure(wraplength=max(200, e.width - 20)))

        self.scroll = ScrollableFrame(self)
        self.scroll.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self._build_form(self.scroll.inner)
        self._build_action_bar()

    def _build_form(self, body: ttk.Frame) -> None:
        pad = {"fill": "x", "padx": (0, 6)}
        bold = ("Segoe UI", 9, "bold")

        src = ttk.LabelFrame(body, text="1. Mã nguồn & Python dùng để build", padding=8)
        src.pack(pady=(0, 6), **pad)
        row = ttk.Frame(src)
        row.pack(fill="x")
        ttk.Label(row, text="File Code (.py):", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Entry(row, textvariable=self.script_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Mở File", command=self._choose_script).pack(side="left")
        row2 = ttk.Frame(src)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Button(row2, text="🔧 Cấu hình Python", command=self._config_python).pack(side="left")
        self.btn_nuitka = ttk.Button(row2, text="Cài Nuitka", command=lambda: self._install_tool("nuitka"))
        self.btn_nuitka.pack(side="left", padx=(8, 0))
        self.btn_pyi = ttk.Button(row2, text="Cài PyInstaller", command=lambda: self._install_tool("pyinstaller"))
        self.btn_pyi.pack(side="left", padx=(4, 0))
        ttk.Label(row2, text="(cài vào đúng python.exe đang hiện ở banner phía trên)", foreground="gray",
                  font=("Segoe UI", 8)).pack(side="left", padx=10)
        row3 = ttk.Frame(src)
        row3.pack(fill="x", pady=(6, 0))
        self.btn_check_imports = ttk.Button(row3, text="🔍 Kiểm tra thư viện", command=lambda: self._check_imports(interactive=True))
        self.btn_check_imports.pack(side="left")
        ttk.Checkbutton(row3, text="Kiểm tra thư viện TRƯỚC & SAU khi build (khuyến nghị - chặn exe thiếu thư viện như pystray)",
                        variable=self.verify_var).pack(side="left", padx=(8, 0))
        self.imports_label = ttk.Label(src, textvariable=self.imports_var, anchor="w", justify="left",
                                       foreground="#475569", font=("Segoe UI", 9))
        self.imports_label.pack(fill="x", pady=(4, 0))
        self.imports_label.bind("<Configure>", lambda e: self.imports_label.configure(wraplength=max(200, e.width - 10)))

        res = ttk.LabelFrame(body, text="2. Tài nguyên đính kèm (Dữ liệu & Icon)", padding=8)
        res.pack(pady=6, **pad)
        res.columnconfigure(0, weight=1)
        lst = ttk.Frame(res)
        lst.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=(0, 8))
        self.data_list = tk.Listbox(lst, height=4, font=("Segoe UI", 9), selectmode="extended")
        sb = ttk.Scrollbar(lst, command=self.data_list.yview)
        self.data_list.config(yscrollcommand=sb.set)
        self.data_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Button(res, text="➕ Thêm File", width=18, command=self._add_files).grid(row=0, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="📁 Thêm Thư mục", width=18, command=self._add_dir).grid(row=1, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="❌ Xoá mục đã chọn", width=18, command=self._remove_selected).grid(row=2, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="🎨 Chọn Icon (.ico)", width=18, command=self._choose_icon).grid(row=3, column=1, sticky="ew", pady=1)
        ttk.Label(res, textvariable=self.icon_var, foreground="gray", font=("Segoe UI", 8)).grid(row=4, column=0, columnspan=2, sticky="w")

        opt = ttk.LabelFrame(body, text="3. Cấu hình Đóng gói & Tối ưu", padding=8)
        opt.pack(pady=6, **pad)
        ttk.Label(opt, text="Trình biên dịch:", font=bold).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Radiobutton(opt, text="Nuitka (biên dịch C, khó dịch ngược)", variable=self.compiler_var, value="Nuitka").grid(row=0, column=1, sticky="w", padx=10)
        ttk.Radiobutton(opt, text="PyInstaller (đóng gói nhanh)", variable=self.compiler_var, value="PyInstaller").grid(row=0, column=2, sticky="w", padx=10)
        ttk.Label(opt, text="Backend C/C++ Nuitka:", font=bold).grid(row=1, column=0, sticky="w", pady=2)
        self.backend_box = ttk.Combobox(opt, textvariable=self.backend_var,
                                        values=list(self.BACKEND_LABELS.values()), state="readonly", width=39)
        self.backend_box.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        ttk.Label(opt, text="Python 3.13: ưu tiên MSVC (nhanh nhờ clcache); tránh MSYS2 UCRT64 và Zig+LTO.",
                  foreground="#9a3412", font=("Segoe UI", 8)).grid(row=1, column=2, sticky="w", padx=10)
        ttk.Label(opt, text="Chế độ xuất:", font=bold).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Radiobutton(opt, text="Onefile (1 file .exe)", variable=self.build_mode_var, value="onefile").grid(row=2, column=1, sticky="w", padx=10)
        ttk.Radiobutton(opt, text="Standalone / Onedir (thư mục, khởi động nhanh)", variable=self.build_mode_var, value="standalone").grid(row=2, column=2, sticky="w", padx=10)
        ttk.Label(opt, text="Màn hình chạy:", font=bold).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Radiobutton(opt, text="Ẩn CMD (ứng dụng GUI)", variable=self.console_mode_var, value="noconsole").grid(row=3, column=1, sticky="w", padx=10)
        ttk.Radiobutton(opt, text="Hiện CMD (ứng dụng console)", variable=self.console_mode_var, value="console").grid(row=3, column=2, sticky="w", padx=10)
        ttk.Label(opt, text="Cờ mở rộng:", font=bold).grid(row=4, column=0, sticky="nw", pady=2)
        flags = ttk.Frame(opt)
        flags.grid(row=4, column=1, columnspan=2, sticky="w", padx=10)
        flag_items = (("Quyền Admin (UAC)", self.uac_var),
                      ("Xoá build/cache sau khi xong (chậm hơn lần sau)", self.clean_var),
                      ("Tối ưu LTO (Nuitka - chậm 2-4x)", self.lto_var),
                      ("Plugin tk-inter (Nuitka)", self.tk_plugin_var),
                      ("Tạo bộ cài (Inno Setup)", self.installer_var),
                      ("Mở thư mục khi xong", self.open_done_var))
        for i, (text, var) in enumerate(flag_items):
            ttk.Checkbutton(flags, text=text, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 14), pady=1)
        iscc = ttk.Frame(opt)
        iscc.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        opt.columnconfigure(2, weight=1)
        ttk.Label(iscc, text="Đường dẫn ISCC:", font=bold).pack(side="left")
        ttk.Entry(iscc, textvariable=self.iscc_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(iscc, text="📁 Chọn ISCC", command=self._choose_iscc).pack(side="left")
        ttk.Button(iscc, text="↻ Dò lại", command=self._redetect_iscc).pack(side="left", padx=(4, 0))

        upg = ttk.LabelFrame(body, text="3b. Nâng cấp / Dọn bản cũ (Inno Setup)", padding=8)
        upg.pack(pady=6, **pad)
        ttk.Checkbutton(upg, text="Tự đóng app đang chạy trước khi cài đè (tránh lỗi \"file đang được sử dụng\")",
                         variable=self.close_apps_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(upg, text="Cảnh báo/chặn khi cài đè bằng bản CŨ HƠN bản đang có trên máy (chống hạ cấp nhầm)",
                         variable=self.warn_downgrade_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(upg, text="Tự khởi động cùng Windows (thêm tuỳ chọn lúc cài đặt, mặc định KHÔNG tick)",
                         variable=self.autostart_var).pack(anchor="w", pady=1)
        ttk.Label(upg, text="Cờ này KHÔNG bắt buộc - chỉ bật nếu phần mềm cần chạy nền/tự mở khi đăng nhập Windows.",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w")
        # ver 1.5: gỡ sạch bản cũ dù bản mới đổi tên phần mềm
        ttk.Checkbutton(upg, text="🧹 Tự GỠ SẠCH mọi bản cũ trước khi cài (kể cả bản cũ mang TÊN PHẦN MỀM KHÁC)",
                        variable=self.uninstall_old_var).pack(anchor="w", pady=(6, 1))
        ttk.Label(upg, text="Nhận diện bản cũ theo TÊN FILE .EXE (vd mọi bản đã cài có NHAN_VIEC.exe) -> tắt tiến trình đang chạy, "
                            "gỡ im lặng, xoá lệnh tự khởi động trỏ vào thư mục cũ. Chạy được cả khi cài im lặng (tự cập nhật).",
                  foreground="gray", font=("Segoe UI", 8), wraplength=900, justify="left").pack(anchor="w", padx=(20, 0))
        ttk.Checkbutton(upg, text="Xoá luôn thư mục cài đặt cũ còn sót (chỉ xoá nếu nằm trong Program Files - dữ liệu ở AppData KHÔNG bị đụng)",
                        variable=self.delete_old_dirs_var).pack(anchor="w", padx=(20, 0), pady=1)
        ttk.Label(upg, text="Gỡ thêm bản cũ có tên khác (mỗi dòng 1 mục: tên .exe cũ, vd may_con.exe - hoặc tiền tố tên phần mềm "
                            "trong Programs and Features, vd NHAN_VIEC). Để trống nếu exe cũ và mới cùng tên:",
                  foreground="gray", font=("Segoe UI", 8), wraplength=900, justify="left").pack(anchor="w", padx=(20, 0), pady=(4, 2))
        old_frame = ttk.Frame(upg)
        old_frame.pack(fill="x", padx=(20, 0))
        self.old_names_text = tk.Text(old_frame, height=2, font=("Consolas", 9))
        self.old_names_text.pack(side="left", fill="both", expand=True)
        old_sb = ttk.Scrollbar(old_frame, command=self.old_names_text.yview)
        self.old_names_text.config(yscrollcommand=old_sb.set)
        old_sb.pack(side="right", fill="y")
        if self._old_names_initial:
            self.old_names_text.insert("1.0", "\n".join(self._old_names_initial))
        ttk.Label(upg, text="File/thư mục dư từ bản cũ cần xoá trước khi cài (mỗi dòng 1 đường dẫn, tính từ thư mục cài đặt - vd: old_module.pyd hoặc old_folder\\):",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 2))
        obs_frame = ttk.Frame(upg)
        obs_frame.pack(fill="x")
        self.obsolete_paths_text = tk.Text(obs_frame, height=3, font=("Consolas", 9))
        self.obsolete_paths_text.pack(side="left", fill="both", expand=True)
        obs_sb = ttk.Scrollbar(obs_frame, command=self.obsolete_paths_text.yview)
        self.obsolete_paths_text.config(yscrollcommand=obs_sb.set)
        obs_sb.pack(side="right", fill="y")
        if self._obsolete_paths_initial:
            self.obsolete_paths_text.insert("1.0", "\n".join(self._obsolete_paths_initial))

        meta = ttk.LabelFrame(body, text="4. Siêu dữ liệu (Metadata bản quyền)", padding=8)
        meta.pack(pady=6, **pad)
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(3, weight=1)
        rows = (("Tên cơ quan:", self.company_var, 0, 0), ("Tên phần mềm:", self.product_var, 0, 2),
                ("Phiên bản (x.x.x.x):", self.version_var, 1, 0), ("Bản quyền:", self.copyright_var, 1, 2),
                ("Tên file .exe (tuỳ chọn):", self.exe_name_var, 2, 0))
        for label, var, r, c in rows:
            ttk.Label(meta, text=label).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 14, 0), pady=2)
            ttk.Entry(meta, textvariable=var).grid(row=r, column=c + 1, sticky="ew", padx=5, pady=2)
        ttk.Label(meta, text="(trống = tự sinh từ tên phần mềm, bỏ dấu cách)", foreground="gray",
                  font=("Segoe UI", 8)).grid(row=2, column=2, columnspan=2, sticky="w", padx=14)
        # ver 1.5: mã nhận diện sản phẩm cố định (đọc/ghi dòng # CC-PRODUCT-ID trong mã nguồn)
        ttk.Label(meta, text="Mã nhận diện sản phẩm:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(6, 2))
        pid_row = ttk.Frame(meta)
        pid_row.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=(6, 2))
        ttk.Entry(pid_row, textvariable=self.product_id_var, width=40, font=("Consolas", 9)).pack(side="left")
        ttk.Button(pid_row, text="🆔 Tạo mã mới", command=self._new_product_id).pack(side="left", padx=(6, 0))
        ttk.Button(pid_row, text="💾 Ghi vào mã nguồn", command=self._save_product_id).pack(side="left", padx=(4, 0))
        ttk.Button(pid_row, text="↻ Đọc lại", command=self._load_product_id).pack(side="left", padx=(4, 0))
        self.pid_label = ttk.Label(meta, textvariable=self.product_id_hint_var, foreground="gray",
                                   font=("Segoe UI", 8), justify="left")
        self.pid_label.grid(row=4, column=0, columnspan=4, sticky="w")
        self.pid_label.bind("<Configure>", lambda e: self.pid_label.configure(wraplength=max(200, e.width - 10)))
        # ver 1.5: phiên bản mà phần mềm TỰ HIỂN THỊ (hằng VERSION trong mã nguồn)
        ttk.Label(meta, text="Phiên bản trong mã nguồn:", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=(6, 2))
        sv_row = ttk.Frame(meta)
        sv_row.grid(row=5, column=1, columnspan=3, sticky="ew", padx=5, pady=(6, 2))
        self.src_version_label = ttk.Label(sv_row, textvariable=self.src_version_var, font=("Segoe UI", 9))
        self.src_version_label.pack(side="left")
        ttk.Button(sv_row, text="⇄ Ghi phiên bản ở ô trên vào mã nguồn",
                   command=self._write_source_version).pack(side="left", padx=(10, 0))
        self.version_var.trace_add("write", lambda *_a: self._load_source_version())

        adv = ttk.LabelFrame(body, text="5. Tham số bổ sung cho trình đóng gói (tuỳ chọn)", padding=6)
        adv.pack(pady=6, **pad)
        ttk.Entry(adv, textvariable=self.extra_var).pack(fill="x")
        ttk.Label(adv, text="Ví dụ: --include-package=mypkg  --nofollow-import-to=tests   (Nuitka)   |   --hidden-import=x   (PyInstaller)",
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))

        # ---- 6. BỘ TĂNG TỐC ----
        perf = ttk.LabelFrame(body, text="6. TURBO - Tăng tốc & tận dụng hiệu năng máy", padding=8)
        perf.pack(pady=(6, 8), **pad)
        perf.columnconfigure(1, weight=1)
        ttk.Label(perf, text="Máy này:", font=bold).grid(row=0, column=0, sticky="nw", pady=2)
        self.hw_label = ttk.Label(perf, textvariable=self.hw_var, foreground="#334155", font=("Segoe UI", 9), justify="left")
        self.hw_label.grid(row=0, column=1, sticky="w", padx=10)
        self.hw_label.bind("<Configure>", lambda e: self.hw_label.configure(wraplength=max(200, e.width - 10)))

        ttk.Label(perf, text="Chế độ:", font=bold).grid(row=1, column=0, sticky="w", pady=2)
        modes = ttk.Frame(perf)
        modes.grid(row=1, column=1, sticky="w", padx=10)
        for text, val in (("🚀 Turbo (toàn bộ CPU, ưu tiên cao)", "turbo"),
                          ("⚖ Cân bằng (chừa 1 lõi)", "balanced"),
                          ("🌱 Tiết kiệm (nửa CPU, ưu tiên thấp - vẫn làm việc khác được)", "eco")):
            ttk.Radiobutton(modes, text=text, variable=self.perf_mode_var, value=val).pack(side="left", padx=(0, 12))

        ttk.Label(perf, text="Luồng biên dịch C:", font=bold).grid(row=2, column=0, sticky="w", pady=2)
        jobs_row = ttk.Frame(perf)
        jobs_row.grid(row=2, column=1, sticky="w", padx=10)
        ttk.Spinbox(jobs_row, from_=0, to=256, width=5, textvariable=self.jobs_var).pack(side="left")
        ttk.Label(jobs_row, textvariable=self.jobs_hint_var, foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=8)

        ttk.Label(perf, text="Tuỳ chọn:", font=bold).grid(row=3, column=0, sticky="nw", pady=2)
        pflags = ttk.Frame(perf)
        pflags.grid(row=3, column=1, sticky="w", padx=10)
        perf_items = (("Ưu tiên CPU cho build (Above Normal)", self.priority_var),
                      ("Chặn máy ngủ khi build", self.keep_awake_var),
                      ("Power plan High Performance khi build", self.power_plan_var),
                      ("Nén payload onefile (tắt = build nhanh, exe to hơn)", self.onefile_compress_var),
                      ("Tinh gọn import dev (pytest/setuptools/IPython)", self.slim_var),
                      ("Bỏ docstring (--python-flag=no_docstrings)", self.nodoc_var))
        for i, (text, var) in enumerate(perf_items):
            ttk.Checkbutton(pflags, text=text, variable=var).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 14), pady=1)

        ttk.Label(perf, text="Nén bộ cài Inno:", font=bold).grid(row=4, column=0, sticky="w", pady=2)
        comp_row = ttk.Frame(perf)
        comp_row.grid(row=4, column=1, sticky="w", padx=10)
        self.comp_box = ttk.Combobox(comp_row, textvariable=self.comp_label_var,
                                     values=list(self.COMPRESSION_LABELS.values()), state="readonly", width=40)
        self.comp_box.pack(side="left")
        ttk.Label(comp_row, textvariable=self.comp_hint_var, foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=8)

        btns = ttk.Frame(perf)
        btns.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 2))
        ttk.Button(btns, text="🛡 Loại trừ Defender (Admin)", command=self._request_defender).pack(side="left")
        ttk.Button(btns, text="↻ Quét lại máy", command=self._probe_hardware).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="📊 Lịch sử build", command=self._show_history).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="📂 Cache Nuitka", command=self._open_cache).pack(side="left", padx=(6, 0))

        ttk.Label(perf, text="Gợi ý:", font=bold).grid(row=6, column=0, sticky="nw", pady=2)
        self.tips_label = ttk.Label(perf, textvariable=self.tips_var, justify="left", foreground="#9a3412", font=("Segoe UI", 9))
        self.tips_label.grid(row=6, column=1, sticky="w", padx=10)
        self.tips_label.bind("<Configure>", lambda e: self.tips_label.configure(wraplength=max(200, e.width - 10)))

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self, padding=(0, 6, 0, 0))
        bar.grid(row=2, column=0, sticky="ew")
        ttk.Separator(bar).pack(fill="x", pady=(0, 8))

        row_btn = ttk.Frame(bar)
        row_btn.pack(fill="x")
        self.btn_build = color_button(row_btn, self.IDLE_TEXT, Palette.RED, self._start_build)
        self.btn_build.config(font=("Segoe UI", 12, "bold"), pady=8)
        self.btn_build.pack(side="left", fill="x", expand=True)
        self.btn_stop = color_button(row_btn, "⛔ Dừng", Palette.SLATE, self._stop_build, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        color_button(row_btn, "📂 Mở dist", Palette.BLUE, self._open_output).pack(side="left", padx=(8, 0))
        color_button(row_btn, "📄 Mở log", Palette.AMBER, self._open_log).pack(side="left", padx=(8, 0))
        self.btn_details = ttk.Button(row_btn, text="▸ Chi tiết", width=10, command=self._toggle_details)
        self.btn_details.pack(side="left", padx=(8, 0))

        row_prog = ttk.Frame(bar)
        row_prog.pack(fill="x", pady=(8, 2))
        self.progressbar = ttk.Progressbar(row_prog, style="Build.Horizontal.TProgressbar", orient="horizontal",
                                           mode="determinate", maximum=100, value=0)
        self.progressbar.pack(side="left", fill="x", expand=True)
        self.pct_label = ttk.Label(row_prog, text="0%", width=5, anchor="e", font=("Segoe UI", 10, "bold"))
        self.pct_label.pack(side="left", padx=(8, 0))
        self.elapsed_label = ttk.Label(row_prog, text="⏱ 00:00", width=10, anchor="e", font=("Consolas", 10))
        self.elapsed_label.pack(side="left")
        self.eta_label = ttk.Label(row_prog, text="", width=16, anchor="e", font=("Consolas", 10), foreground="#64748b")
        self.eta_label.pack(side="left")

        self.status_label = ttk.Label(bar, textvariable=self.status_var, anchor="w",
                                      foreground=self.STATUS_COLORS["info"], font=("Segoe UI", 9))
        self.status_label.pack(fill="x", pady=(0, 4))
        self.status_label.bind("<Configure>", lambda e: self.status_label.configure(wraplength=max(200, e.width - 10)))

        self.details_frame = ttk.LabelFrame(bar, text="Nhật ký chi tiết (toàn bộ đã được ghi ra file log)", padding=4)
        self.console = ConsoleText(self.details_frame, bg="#0f172a", fg="#e2e8f0", height=9)
        self.console.pack(fill="both", expand=True)
        if self.details_visible:
            self._show_details(True)

    # ---------------- tiến độ / trạng thái ----------------
    def _set_status(self, text: str, kind: str = "info") -> None:
        self.status_var.set(text)
        self.status_label.configure(foreground=self.STATUS_COLORS.get(kind, self.STATUS_COLORS["info"]))

    def _set_bar_color(self, color: str) -> None:
        self.style.configure("Build.Horizontal.TProgressbar", background=color, lightcolor=color, darkcolor=color)

    def _apply_progress(self) -> None:
        if not self.progress:
            return
        value = self.progress.value
        self.progressbar["value"] = value
        self.pct_label.config(text=f"{int(value)}%")
        if self.pipeline:
            self.btn_build.config(text=f"⏳ ĐANG ĐÓNG GÓI... {int(value)}%")

    def _start_tick(self) -> None:
        self._t0 = time.monotonic()
        self._stop_tick()
        self._tick_job = self.after(250, self._tick)

    def _tick(self) -> None:
        self._tick_job = None
        if not self.pipeline:
            return
        try:
            elapsed = time.monotonic() - self._t0
            if self.progress:
                self.progress.tick(0.25, elapsed)
                eta = self.progress.eta(elapsed)
                if eta is None:
                    self.eta_label.config(text="")
                elif eta > 0:
                    self.eta_label.config(text=f"còn ~{fmt_elapsed(eta)}")
                else:
                    self.eta_label.config(text="sắp xong...")
            self._apply_progress()
            self.elapsed_label.config(text="⏱ " + fmt_elapsed(elapsed))
        except tk.TclError:
            return
        self._tick_job = self.after(250, self._tick)

    def _stop_tick(self) -> None:
        if self._tick_job is not None:
            try:
                self.after_cancel(self._tick_job)
            except tk.TclError:
                pass
            self._tick_job = None

    def _schedule_status_refresh(self) -> None:
        if self._status_job is None:
            self._status_job = self.after(150, self._refresh_status)

    def _refresh_status(self) -> None:
        self._status_job = None
        if not self.pipeline or not self.progress:
            return
        text = self.progress.label
        if self._last_line:
            text += "   ·   " + self._last_line
        self._set_status(text, "info")

    def _toggle_details(self) -> None:
        self._show_details(not self.details_visible)

    def _show_details(self, show: bool) -> None:
        self.details_visible = show
        if show:
            self.details_frame.pack(fill="both", expand=True, pady=(0, 4))
            self.btn_details.config(text="▾ Chi tiết")
        else:
            self.details_frame.pack_forget()
            self.btn_details.config(text="▸ Chi tiết")

    # ---------------- TURBO: dò máy, gợi ý, Defender, lịch sử ----------------
    def _project_dir(self) -> str:
        script = self.script_var.get().strip()
        return os.path.dirname(os.path.abspath(script)) if script else ""

    def _jobs_value(self) -> int:
        try:
            return max(0, min(256, int(float(self.jobs_var.get().strip() or "0"))))
        except ValueError:
            return 0

    def _compression_key(self) -> str:
        return next((k for k, v in self.COMPRESSION_LABELS.items() if v == self.comp_label_var.get()), "balanced")

    def _obsolete_paths_list(self) -> list[str]:
        if self.obsolete_paths_text is None:
            return []
        raw = self.obsolete_paths_text.get("1.0", "end")
        return [line.strip().strip("/\\") for line in raw.splitlines() if line.strip()]

    def _old_names_list(self) -> list[str]:
        if self.old_names_text is None:
            return []
        return [ln.strip() for ln in self.old_names_text.get("1.0", "end").splitlines() if ln.strip()]

    def _backend_key(self) -> str:
        return next((key for key, label in self.BACKEND_LABELS.items() if label == self.backend_var.get()), "msvc")

    def _history_key(self) -> str:
        script = self.script_var.get().strip()
        if not script:
            return ""
        tag = self._compression_key() if self.installer_var.get() else "off"
        return BuildHistory.make_key(script, self.compiler_var.get(), self._backend_key(),
                                     self.build_mode_var.get(), self.lto_var.get(), tag)

    def _perf_context(self) -> PerfContext:
        key = self._history_key()
        exp = BuildHistory.expected(key) if key else None
        return PerfContext(
            compiler=self.compiler_var.get(), backend=self._backend_key(), lto=self.lto_var.get(),
            clean_build=self.clean_var.get(), onefile=self.build_mode_var.get() == "onefile",
            onefile_compress=self.onefile_compress_var.get(), installer=self.installer_var.get(),
            installer_compression=self._compression_key(), perf_mode=self.perf_mode_var.get(),
            jobs=self._jobs_value(), power_plan_enabled=self.power_plan_var.get(),
            python_bits=self.py_info.bits if self.py_info else 64, project_dir=self._project_dir(),
            last_total=exp["total"] if exp else None,
        )

    def _schedule_tips(self) -> None:
        if self._tips_job is None:
            try:
                self._tips_job = self.after(200, self._refresh_tips)
            except tk.TclError:
                pass

    def _refresh_tips(self) -> None:
        self._tips_job = None
        ctx = self._perf_context()
        tips = PerformanceAdvisor.tips(self.hw, ctx)
        self.tips_var.set("\n".join(tips[:7]))
        hw = self.hw or HardwareProfile.quick()
        rec = recommend_jobs(hw, ctx.perf_mode, ctx.lto)
        ram_note = f", RAM {hw.ram_total_gb:.0f} GB" if hw.ram_total_gb else ""
        self.jobs_hint_var.set(f"0 = tự động → đề xuất {rec} luồng (máy {hw.cpu} lõi{ram_note})")
        if ctx.installer_compression == "none":
            self.comp_hint_var.set("bỏ qua bước nén")
        else:
            threads = installer_threads_for(hw, ctx.perf_mode, ctx.installer_compression)
            self.comp_hint_var.set(f"LZMA2 đa luồng: {threads} luồng, tiến trình 64-bit riêng")

    def _probe_hardware(self) -> None:
        if self._probing_hw:
            return
        self._probing_hw = True
        project_dir = self._project_dir()
        self.hw_var.set("⏳ đang quét phần cứng, power plan & Defender (vài giây)...")

        def worker() -> None:
            hw = HardwareProfile.probe(project_dir, check_defender=True)
            self.app.dispatch(self._apply_hardware, hw)

        threading.Thread(target=worker, daemon=True, name="probe-hw").start()

    def _apply_hardware(self, hw: HardwareProfile) -> None:
        self._probing_hw = False
        self.hw = hw
        self.hw_var.set(hw.summary())
        self.console.append(f"> [TURBO] {hw.summary()}\n", "info")
        self._refresh_tips()

    def _request_defender(self) -> None:
        if not IS_WINDOWS:
            messagebox.showinfo("Chỉ Windows", "Tính năng này chỉ áp dụng cho Windows Defender.", parent=self)
            return
        paths: list[str] = []
        project_dir = self._project_dir()
        if project_dir:
            paths.append(project_dir)
        paths += DefenderHelper.cache_dirs()
        if not paths:
            messagebox.showinfo("Chưa có đường dẫn", "Hãy chọn file .py trước để biết thư mục dự án.", parent=self)
            return
        body = ("Sẽ mở PowerShell với quyền Admin (hộp thoại UAC) để thêm loại trừ quét realtime "
                "của Windows Defender cho:\n\n" + "\n".join(f"• {p}" for p in paths) +
                "\n\nChỉ cần làm 1 lần cho mỗi dự án. Tiếp tục?")
        if not messagebox.askyesno("Loại trừ Windows Defender", body, parent=self):
            return
        ok = DefenderHelper.request_exclusion(paths)
        if ok:
            self._set_status("Đã gửi yêu cầu loại trừ Defender; sẽ quét lại máy sau vài giây...", "ok")
            self.after(5000, self._probe_hardware)
        else:
            self._set_status("Bạn đã huỷ UAC hoặc không mở được PowerShell với quyền Admin.", "warn")

    def _show_history(self) -> None:
        key = self._history_key()
        if not key:
            messagebox.showinfo("Chưa chọn file", "Hãy chọn file .py trước.", parent=self)
            return
        runs = BuildHistory.runs(key)
        if not runs:
            messagebox.showinfo("Lịch sử build", "Chưa có lần build nào với cấu hình này.\n"
                                "Sau lần build đầu tiên, thanh tiến độ và ETA sẽ dựa trên thời gian thực.", parent=self)
            return
        lines = [f"{r.get('when', '?')}   {'OK  ' if r.get('ok') else 'FAIL'}   {fmt_elapsed(float(r.get('total', 0)))}"
                 f"   jobs={r.get('jobs', '?')}   {r.get('perf', '?')}" for r in reversed(runs)]
        messagebox.showinfo("Lịch sử build (cấu hình hiện tại)", "\n".join(lines), parent=self)

    def _open_cache(self) -> None:
        for p in DefenderHelper.cache_dirs():
            if os.path.isdir(p):
                open_in_explorer(p)
                return
        messagebox.showinfo("Cache", "Chưa có thư mục cache Nuitka/PyInstaller (sẽ xuất hiện sau lần build đầu).\n"
                            "Giữ nguyên cache này để các lần build sau nhanh hơn.", parent=self)

    # ---------------- dò công cụ (thread nền) ----------------
    def _detect_tools(self, custom_iscc: str) -> None:
        info = self.locator.resolve()
        self.app.dispatch(self._apply_python_info, info)
        if not os.path.isfile(custom_iscc):
            found = IsccLocator.find()
            self.app.dispatch(self._apply_iscc, found)

    def _apply_python_info(self, info: Optional[PythonInfo]) -> None:
        self.py_info = info
        if info:
            prefix = "⚠ Đang chạy dạng .exe → dùng Python ngoài: " if is_frozen() else "Python dùng để build: "
            self.tools_var.set(f"{prefix}{info.path}\n{info.describe()}")
            needs_msvc = IS_WINDOWS and NuitkaToolchain.python_major_minor(info) >= (3, 13)
            banner_color = "#166534" if (info.nuitka or info.pyinstaller) and (info.msvc or not needs_msvc) else "#a16207"
            self.banner.config(bg=banner_color)
            self.console.append(f"> {info.describe()}\n", "info")
            if needs_msvc and not info.msvc:
                self.console.append("> Python 3.13+ nhưng CHƯA thấy MSVC: cài Visual Studio Build Tools 2022 "
                                    "(Desktop development with C++) hoặc chọn backend Zig KHÔNG bật LTO.\n", "warn")
        else:
            self.tools_var.set("⚠ CHƯA tìm thấy python.exe hợp lệ. Bấm '🔧 Cấu hình Python' để chọn thủ công.")
            self.banner.config(bg="#b91c1c")
        self._schedule_tips()
        if info and not self.pipeline:
            self._check_imports(interactive=False)   # ver 1.5: Python build vừa đổi/cài thêm gói -> kiểm lại

    def _apply_iscc(self, found: Optional[str]) -> None:
        if found:
            self.iscc_var.set(found)
            self.console.append(f"> Inno Setup: {found}\n", "info")
        else:
            self.console.append("> Inno Setup: không tìm thấy ISCC.exe (có thể chọn thủ công hoặc bỏ tick 'Tạo bộ cài').\n", "warn")

    def _redetect_iscc(self) -> None:
        self.iscc_var.set("")
        threading.Thread(target=lambda: self.app.dispatch(self._apply_iscc, IsccLocator.find()),
                         daemon=True, name="detect-iscc").start()

    def _config_python(self) -> None:
        picked = filedialog.askopenfilename(title="Chọn file python.exe",
                                            filetypes=[("python.exe", "python*.exe"), ("Tất cả", "*.*")], parent=self)
        if not picked:
            return
        self._set_status(f"Đang kiểm tra {picked} ...", "info")
        self.console.append(f"> Đang kiểm tra {picked} ...\n", "info")

        def worker() -> None:
            info, err = self.locator.remember(picked)
            if info:
                self.app.dispatch(self._apply_python_info, info)
                self.app.dispatch(self._set_status, f"Đã ghi nhớ python.exe: {picked}", "ok")
                self.app.dispatch(self.console.append, f"[HỆ THỐNG] Đã ghi nhớ python.exe: {picked}\n", "ok")
            else:
                self.app.dispatch(self._set_status, "python.exe không hợp lệ.", "err")
                self.app.dispatch(messagebox.showerror, "Không dùng được", err, parent=self)

        threading.Thread(target=worker, daemon=True, name="probe-python").start()

    def _install_tool(self, package: str) -> None:
        if not self.py_info:
            messagebox.showwarning("Chưa có Python", "Hãy cấu hình python.exe trước.", parent=self)
            return
        if self.tool_busy or self.pipeline:
            return
        if not messagebox.askyesno("Cài đặt", f"Chạy: pip install --upgrade {package}\nvào {self.py_info.path}?", parent=self):
            return
        self.tool_busy = True
        self._show_details(True)
        python_exe = self.py_info.path
        cmd = PythonLocator.pip_install_command(python_exe, package)
        self._set_status(f"Đang cài {package} ...", "info")
        self.console.append(f"\n> {subprocess.list2cmdline(cmd)}\n", "info")

        def worker() -> None:
            rc = ProcessRunner().run(cmd, cwd=None, on_line=lambda s: self.app.dispatch(self.console.append, s))
            info = self.locator.probe(python_exe)
            if info:
                info.msvc = NuitkaToolchain.find_msvc() or ""
            self.app.dispatch(self._apply_python_info, info)
            self.app.dispatch(self.console.append, f"> pip kết thúc với mã {rc}\n", "ok" if rc == 0 else "err")
            self.app.dispatch(self._set_status, f"Cài {package}: {'xong' if rc == 0 else 'LỖI, xem Chi tiết'}",
                              "ok" if rc == 0 else "err")
            self.tool_busy = False

        threading.Thread(target=worker, daemon=True, name="pip").start()

    # ---------------- chọn file / tài nguyên ----------------
    def _choose_script(self) -> None:
        path = filedialog.askopenfilename(title="Chọn file Python gốc",
                                          filetypes=[("Python", "*.py *.pyw"), ("Tất cả", "*.*")], parent=self)
        if not path:
            return
        self.script_var.set(path)
        self.console.append(f"> Đã nạp file: {os.path.basename(path)}\n", "info")
        try:
            source = Path(path).read_text(encoding="utf-8", errors="ignore")
            uses_tk = re.search(r"^\s*(?:import|from)\s+tkinter", source, re.M) is not None
            self.tk_plugin_var.set(uses_tk)
            note = f"Đã nạp {os.path.basename(path)} · tkinter: {'CÓ' if uses_tk else 'không'} → plugin tk-inter {'bật' if uses_tk else 'tắt'}"
            self._set_status(note, "ok")
            self.console.append(f"> {note}\n", "info")
        except OSError:
            self._set_status(f"Đã nạp {os.path.basename(path)}", "ok")
        self._probe_hardware()   # dự án có thể nằm trên ổ khác / trong OneDrive -> dò lại
        self._schedule_tips()
        self._check_imports(interactive=False)   # ver 1.5: báo sớm thư viện còn thiếu
        self._load_product_id()
        self._load_source_version()

    # ---------------- ver 1.5: kiểm tra thư viện ----------------
    def _show_import_report(self, report: ImportReport) -> None:
        """Cập nhật dòng tóm tắt dưới mục 1 + ghi chi tiết ra console."""
        for line in report.summary_lines():
            tag = "err" if line.startswith("✗") else ("warn" if line.startswith("⚠") else "info")
            self.console.append(f"> [THƯ VIỆN] {line}\n", tag)
        if report.error:
            self.imports_var.set(f"⚠ Không kiểm tra được thư viện: {report.error[:200]}")
            self.imports_label.configure(foreground=self.STATUS_COLORS["warn"])
        elif report.missing():
            names = ", ".join(f"{m.name} (pip: {m.pip_name})" for m in report.missing())
            self.imports_var.set(f"✗ Python build THIẾU: {names} → build ra exe sẽ chạy thiếu tính năng. "
                                 "Bấm '🔍 Kiểm tra thư viện' để cài.")
            self.imports_label.configure(foreground=self.STATUS_COLORS["err"])
        else:
            tp = report.third_party()
            names = ", ".join(m.name for m in tp) if tp else "chỉ dùng thư viện chuẩn"
            self.imports_var.set(f"✓ Đủ thư viện ({len(tp)} bên thứ 3: {names})")
            self.imports_label.configure(foreground=self.STATUS_COLORS["ok"])

    def _check_imports(self, interactive: bool, then: Optional[Callable[[ImportReport], None]] = None) -> None:
        """Chạy ImportChecker ở thread nền. interactive=True: hiện hộp thoại kết quả / đề nghị cài.
        then: callback (luồng UI) nhận kết quả - dùng cho bước kiểm tra trước khi build."""
        script = self.script_var.get().strip()
        if not script or not os.path.isfile(script):
            if interactive:
                messagebox.showinfo("Chưa chọn file", "Hãy chọn file .py trước.", parent=self)
            return
        if not self.py_info:
            if interactive:
                messagebox.showwarning("Chưa có Python", "Hãy cấu hình python.exe trước.", parent=self)
            return
        if self._checking_imports:
            if then is not None:   # đang có lượt kiểm tra khác (vd vừa chọn file) -> chạy lại ngay sau lượt đó
                self._import_waiters.append(then)
            return
        self._checking_imports = True
        self.btn_check_imports.config(state="disabled")
        self.imports_var.set(f"⏳ Đang kiểm tra thư viện của {os.path.basename(script)} trong {self.py_info.path} ...")
        self.imports_label.configure(foreground=self.STATUS_COLORS["info"])
        python_exe = self.py_info.path

        def worker() -> None:
            try:
                report = ImportChecker.check(script, python_exe)
            except Exception as exc:  # noqa: BLE001
                log.exception("ImportChecker lỗi")
                report = ImportReport(python=python_exe, error=str(exc))
            self.app.dispatch(self._on_import_report, report, interactive, then)

        threading.Thread(target=worker, daemon=True, name="check-imports").start()

    def _on_import_report(self, report: ImportReport, interactive: bool,
                          then: Optional[Callable[[ImportReport], None]]) -> None:
        self._checking_imports = False
        self.btn_check_imports.config(state="normal")
        self._show_import_report(report)
        waiters, self._import_waiters = self._import_waiters, []
        for waiter in waiters:   # kiểm tra lại với cấu hình mới nhất rồi mới giao kết quả
            self._check_imports(interactive=False, then=waiter)
        if then is not None:
            then(report)
            return
        if not interactive:
            if report.missing():
                self._set_status("⚠ Python build còn THIẾU thư viện: "
                                 + ", ".join(m.name for m in report.missing()), "warn")
            return
        if report.error:
            messagebox.showwarning("Kiểm tra thư viện", f"Không kiểm tra được:\n{report.error}", parent=self)
        elif report.missing():
            if messagebox.askyesno("Thiếu thư viện", self._missing_text(report) +
                                   "\n\nCài ngay vào đúng Python build?", parent=self):
                self._pip_install(report.pip_packages(),
                                  after=lambda ok: self._check_imports(interactive=True) if ok else None)
        else:
            messagebox.showinfo("Kiểm tra thư viện", "\n".join(report.summary_lines()), parent=self)

    def _missing_text(self, report: ImportReport) -> str:
        lines = [f"Python dùng để build:\n{report.python}\n\nCHƯA CÓ các thư viện mà code cần:"]
        for m in report.missing():
            risk = " ← lỗi bị try/except NUỐT, exe sẽ âm thầm thiếu tính năng" if m.guarded else ""
            lines.append(f"• {m.name}  (pip install {m.pip_name})\n   import tại {m.first_use()}{risk}")
        return "\n".join(lines)

    def _pip_install(self, packages: list[str], after: Optional[Callable[[bool], None]] = None) -> None:
        if not self.py_info or not packages or self.tool_busy or self.pipeline:
            return
        self.tool_busy = True
        self._show_details(True)
        python_exe = self.py_info.path
        cmd = [python_exe, "-m", "pip", "install", "--upgrade", *packages]
        self._set_status(f"Đang cài {' '.join(packages)} ...", "info")
        self.console.append(f"\n> {subprocess.list2cmdline(cmd)}\n", "info")

        def worker() -> None:
            rc = ProcessRunner().run(cmd, cwd=None, on_line=lambda s: self.app.dispatch(self.console.append, s))
            self.app.dispatch(self._on_pip_done, packages, rc, after)

        threading.Thread(target=worker, daemon=True, name="pip").start()

    def _on_pip_done(self, packages: list[str], rc: int, after: Optional[Callable[[bool], None]]) -> None:
        self.tool_busy = False
        ok = rc == 0
        self.console.append(f"> pip kết thúc với mã {rc}\n", "ok" if ok else "err")
        self._set_status(f"Cài {' '.join(packages)}: {'xong' if ok else 'LỖI, xem Chi tiết'}", "ok" if ok else "err")
        if not ok:
            messagebox.showerror("Cài thư viện thất bại",
                                 f"pip trả về mã lỗi {rc}. Xem mục 'Chi tiết' để biết nguyên nhân "
                                 "(mạng, quyền ghi, tên gói...).", parent=self)
        if after is not None:
            after(ok)

    # ---------------- ver 1.5: mã nhận diện sản phẩm ----------------
    PID_HELP = ("Mã này nằm trong mã nguồn (dòng '# CC-PRODUCT-ID: ...') và đi theo phần mềm qua mọi phiên bản → "
                "bộ cài luôn nhận ra & gỡ bản cũ dù đổi tên phần mềm/tên exe. KHÔNG chép mã sang phần mềm khác.")

    def _set_pid_hint(self, text: str, kind: str = "info") -> None:
        self.product_id_hint_var.set(f"{text}\n{self.PID_HELP}")
        colors = {"info": "gray", "ok": self.STATUS_COLORS["ok"], "warn": self.STATUS_COLORS["warn"],
                  "err": self.STATUS_COLORS["err"]}
        self.pid_label.configure(foreground=colors.get(kind, "gray"))

    def _load_product_id(self) -> None:
        script = self.script_var.get().strip()
        if not script or not os.path.isfile(script):
            self.product_id_var.set("")
            self._set_pid_hint("Chọn file .py để đọc mã nhận diện.")
            return
        pid = ProductIdentity.read(script)
        self.product_id_var.set(pid)
        if pid:
            self._set_pid_hint(f"✓ Đọc từ mã nguồn {os.path.basename(script)} - AppId bộ cài cố định theo mã này.", "ok")
        else:
            self._set_pid_hint(f"⚠ {os.path.basename(script)} CHƯA có mã nhận diện. Nếu đây là phiên bản mới của phần mềm "
                               "đã có mã, dán mã cũ vào ô rồi bấm 'Ghi vào mã nguồn'; nếu là phần mềm mới, bấm 'Tạo mã mới'. "
                               "(Khi build sẽ được hỏi lại.)", "warn")

    # ---------------- ver 1.5: phiên bản trong mã nguồn ----------------
    def _load_source_version(self) -> None:
        if not hasattr(self, "src_version_label"):
            return
        script = self.script_var.get().strip()
        found = SourceVersion.read(script) if script and os.path.isfile(script) else None
        if not found:
            self.src_version_var.set("(không thấy hằng VERSION / APP_VERSION / __version__ ở cấp module - bỏ qua)")
            self.src_version_label.configure(foreground="gray")
            return
        name, value, line = found
        if SourceVersion.same(value, self.version_var.get()):
            self.src_version_var.set(f"✓ {name} = \"{value}\" (dòng {line}) - khớp phiên bản build")
            self.src_version_label.configure(foreground=self.STATUS_COLORS["ok"])
        else:
            self.src_version_var.set(f"✗ {name} = \"{value}\" (dòng {line}) - LỆCH với {self.version_var.get().strip()}: "
                                     "phần mềm sẽ tự hiển thị/tự so cập nhật theo số này!")
            self.src_version_label.configure(foreground=self.STATUS_COLORS["err"])

    def _write_source_version(self) -> bool:
        script = self.script_var.get().strip()
        found = SourceVersion.read(script) if script and os.path.isfile(script) else None
        version = normalize_version(self.version_var.get())
        if not found:
            messagebox.showinfo("Không thấy hằng phiên bản",
                                "Mã nguồn không có dòng VERSION = \"...\" (hoặc APP_VERSION / __version__) ở cấp module.",
                                parent=self)
            return False
        try:
            SourceVersion.write(script, version)
        except (OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Không ghi được", f"Không ghi được phiên bản vào {script}:\n{exc}", parent=self)
            return False
        self.console.append(f"> [PHIÊN BẢN] {found[0]} = \"{found[1]}\" -> \"{version}\" trong "
                            f"{os.path.basename(script)} (dòng {found[2]})\n", "ok")
        self._load_source_version()
        return True

    def _ensure_source_version(self, cfg: BuildConfig) -> bool:
        """Trước khi build: phiên bản trong mã nguồn phải khớp ô Phiên bản. False = huỷ build."""
        found = SourceVersion.read(cfg.script)
        if not found or SourceVersion.same(found[1], cfg.version):
            return True
        name, value, line = found
        ans = messagebox.askyesnocancel(
            "Phiên bản trong mã nguồn bị LỆCH",
            f"Ô Phiên bản     : {cfg.version}\n"
            f"Trong mã nguồn  : {name} = \"{value}\"  ({os.path.basename(cfg.script)}, dòng {line})\n\n"
            "Phần mềm tự HIỂN THỊ và tự SO KHI CẬP NHẬT theo số trong mã nguồn → nếu để lệch, mở lên vẫn "
            f"thấy bản {value}, và cơ chế tự cập nhật có thể cài lại liên tục.\n\n"
            f"Yes/Có = sửa mã nguồn thành \"{cfg.version}\" rồi build (khuyến nghị)\n"
            "No/Không = vẫn build, giữ nguyên mã nguồn\nCancel = huỷ", icon="warning", parent=self)
        if ans is None:
            return False
        if ans:
            return self._write_source_version()
        self.console.append(f"> [PHIÊN BẢN] Người dùng giữ {name} = \"{value}\" lệch với {cfg.version}\n", "warn")
        return True

    def _ensure_stable_names(self, cfg: BuildConfig) -> bool:
        """Tên exe/tên phần mềm chứa số phiên bản -> mỗi bản 1 tên exe khác (lệnh tự khởi động, gỡ bản cũ
        theo tên exe, lối tắt... đều lệch). Chỉ cảnh báo, không tự sửa."""
        v = cfg.version.split(".")
        tokens = {".".join(v[:n]) for n in (2, 3, 4)} | {"_".join(v[:n]) for n in (2, 3, 4)}
        hits = [label for label, name in (("Tên file .exe", cfg.exe_stem), ("Tên phần mềm", cfg.product))
                if any(t in name for t in tokens)]
        if not hits:
            return True
        return messagebox.askyesno(
            "Tên chứa số phiên bản",
            f"{' và '.join(hits)} đang chứa số phiên bản ({cfg.exe_stem} / {cfg.product}).\n\n"
            "Nên đặt tên CỐ ĐỊNH (vd exe = NHAN_VIEC, phần mềm = NHAN_VIEC) - số phiên bản đã được Windows "
            "tự ghi kèm trong Programs and Features. Nếu tên đổi theo từng bản: mỗi bản cài vào 1 thư mục "
            "khác, lối tắt/lệnh tự khởi động đổi tên theo.\n\n"
            "Vẫn build với tên hiện tại?", icon="warning", parent=self)

    def _new_product_id(self) -> None:
        if self.product_id_var.get().strip() and not messagebox.askyesno(
                "Tạo mã mới?", "Ô đang có mã. Tạo mã MỚI nghĩa là bộ cài sẽ coi đây là phần mềm KHÁC "
                "(chỉ còn nhận bản cũ qua tên exe).\nChỉ làm vậy nếu đây thật sự là phần mềm mới. Tiếp tục?",
                icon="warning", parent=self):
            return
        self.product_id_var.set(ProductIdentity.new_id())
        self._save_product_id()

    def _save_product_id(self) -> bool:
        script = self.script_var.get().strip()
        pid = ProductIdentity.normalize(self.product_id_var.get())
        if not script or not os.path.isfile(script):
            messagebox.showinfo("Chưa chọn file", "Hãy chọn file .py trước.", parent=self)
            return False
        if not pid:
            messagebox.showerror("Mã không hợp lệ", "Mã phải có dạng XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX "
                                 "(bấm 'Tạo mã mới' để sinh tự động).", parent=self)
            return False
        try:
            ProductIdentity.write(script, pid)
        except (OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Không ghi được", f"Không ghi được mã vào {script}:\n{exc}", parent=self)
            return False
        self.product_id_var.set(pid)
        self.console.append(f"> [MÃ SẢN PHẨM] Đã ghi '# CC-PRODUCT-ID: {pid}' vào {os.path.basename(script)}\n", "ok")
        self._set_pid_hint(f"✓ Đã ghi vào mã nguồn {os.path.basename(script)}.", "ok")
        return True

    def _ensure_product_id(self, cfg: BuildConfig) -> bool:
        """Trước khi build: thống nhất mã trong ô với mã trong mã nguồn, gán vào cfg. False = huỷ build."""
        code_pid = ProductIdentity.read(cfg.script)
        raw = self.product_id_var.get().strip()
        ui_pid = ProductIdentity.normalize(raw)
        if raw and not ui_pid:
            messagebox.showerror("Mã không hợp lệ", f"Mã nhận diện '{raw}' không đúng định dạng.", parent=self)
            return False
        if code_pid and ui_pid and code_pid != ui_pid:
            ans = messagebox.askyesnocancel(
                "Mã nhận diện khác nhau",
                f"Mã trong mã nguồn : {code_pid}\nMã đang nhập ở ô : {ui_pid}\n\n"
                "Yes/Có = ghi đè mã trong mã nguồn bằng mã đang nhập\nNo/Không = dùng mã trong mã nguồn\nCancel = huỷ build",
                icon="warning", parent=self)
            if ans is None:
                return False
            if ans and not self._save_product_id():
                return False
            cfg.product_id = ui_pid if ans else code_pid
        elif code_pid:
            cfg.product_id = code_pid
        elif ui_pid:
            if messagebox.askyesno("Ghi mã vào mã nguồn?",
                                   f"Ghi mã nhận diện {ui_pid} vào {os.path.basename(cfg.script)} để các phiên bản sau "
                                   "tự dùng lại?", parent=self):
                self._save_product_id()
            cfg.product_id = ui_pid
        elif cfg.make_installer:
            ans = messagebox.askyesnocancel(
                "Chưa có mã nhận diện sản phẩm",
                f"{os.path.basename(cfg.script)} chưa có mã nhận diện sản phẩm.\n\n"
                "Có mã này thì mọi phiên bản sau (dù đổi tên phần mềm/tên exe) đều được bộ cài nhận ra "
                "và tự gỡ bản cũ.\n\n"
                "Yes/Có = tạo mã mới & ghi vào mã nguồn (phần mềm MỚI, hoặc lần đầu dùng mã)\n"
                "No/Không = build không có mã (như cũ, chỉ nhận bản cũ qua tên exe)\n"
                "Cancel = huỷ để dán mã của phiên bản trước vào ô", parent=self)
            if ans is None:
                return False
            if ans:
                self.product_id_var.set(ProductIdentity.new_id())
                if not self._save_product_id():
                    return False
                cfg.product_id = self.product_id_var.get()
        return True

    def _refresh_data_list(self) -> None:
        self.data_list.delete(0, "end")
        for kind, path in self.data_items:
            self.data_list.insert("end", ("📁 " if kind == "dir" else "📄 ") + path)

    def _add_files(self) -> None:
        for f in filedialog.askopenfilenames(title="Chọn file dữ liệu đính kèm", parent=self):
            if ("file", f) not in self.data_items:
                self.data_items.append(("file", f))
        self._refresh_data_list()

    def _add_dir(self) -> None:
        d = filedialog.askdirectory(title="Chọn thư mục dữ liệu đính kèm", parent=self)
        if d and ("dir", d) not in self.data_items:
            self.data_items.append(("dir", d))
            self._refresh_data_list()

    def _remove_selected(self) -> None:
        for idx in sorted(self.data_list.curselection(), reverse=True):
            del self.data_items[idx]
        self._refresh_data_list()

    def _choose_icon(self) -> None:
        path = filedialog.askopenfilename(title="Chọn Icon", filetypes=[("Icon", "*.ico")], parent=self)
        if path:
            self.icon_var.set(path)
            self._ensure_icon_bundled(path)

    def _ensure_icon_bundled(self, path: str) -> None:
        """Icon chỉ chọn ở đây (--windows-icon-from-ico/--icon) chỉ gắn icon cho FILE .exe
        (Explorer/taskbar) - phần mềm KHÔNG tự đọc được file này lúc chạy, nên nếu code Python
        tự vẽ icon khay hệ thống (system tray, vd bằng pystray/infi.systray) mà không thấy icon
        là do thiếu bước này. Tự thêm icon vào "Tài nguyên đính kèm" để nó được nhúng cùng
        (--include-data-files), và trong code có thể dò icon cạnh exe bằng đúng cách hàm
        _duong_dan_tai_nguyen() ở đầu file này đang làm cho chính Control Center."""
        if ("file", path) not in self.data_items:
            self.data_items.append(("file", path))
            self._refresh_data_list()

    def _choose_iscc(self) -> None:
        path = filedialog.askopenfilename(title="Chọn file ISCC.exe",
                                          filetypes=[("ISCC", "ISCC.exe"), ("Tất cả", "*.*")], parent=self)
        if path:
            self.iscc_var.set(path)

    def _open_output(self) -> None:
        script = self.script_var.get().strip()
        if not script:
            messagebox.showinfo("Chưa chọn file", "Hãy chọn file .py trước để biết thư mục dự án.", parent=self)
            return
        base = os.path.dirname(os.path.abspath(script))
        dist = os.path.join(base, "dist")
        open_in_explorer(dist if os.path.isdir(dist) else base)

    def _open_log(self) -> None:
        if self.last_log_path and os.path.isfile(self.last_log_path):
            open_in_explorer(self.last_log_path)
            return
        script = self.script_var.get().strip()
        folder = os.path.join(os.path.dirname(os.path.abspath(script)), "build_logs") if script else ""
        if folder and os.path.isdir(folder):
            open_in_explorer(folder)
        else:
            messagebox.showinfo("Chưa có log",
                                "Chưa có lần đóng gói nào cho dự án này.\n"
                                "Sau mỗi lần build, log được ghi vào <thư mục dự án>\\build_logs\\", parent=self)

    # ---------------- build ----------------
    def snapshot(self) -> BuildConfig:
        assert self.py_info is not None
        return BuildConfig(
            script=self.script_var.get().strip(), python=self.py_info,
            compiler=self.compiler_var.get(), build_mode=self.build_mode_var.get(),
            nuitka_backend=self._backend_key(),
            console_mode=self.console_mode_var.get(), uac_admin=self.uac_var.get(),
            clean_build=self.clean_var.get(), lto=self.lto_var.get(), tk_plugin=self.tk_plugin_var.get(),
            icon=self.icon_var.get().strip(),
            data_files=[p for k, p in self.data_items if k == "file"],
            data_dirs=[p for k, p in self.data_items if k == "dir"],
            company=self.company_var.get().strip(), product=self.product_var.get().strip(),
            exe_name=self.exe_name_var.get().strip(), version=normalize_version(self.version_var.get()),
            copyright=self.copyright_var.get().strip(), extra_args=self.extra_var.get(),
            make_installer=self.installer_var.get(), iscc_path=self.iscc_var.get().strip(),
            perf_mode=self.perf_mode_var.get(), jobs=self._jobs_value(), high_priority=self.priority_var.get(),
            keep_awake=self.keep_awake_var.get(), power_plan=self.power_plan_var.get(),
            onefile_compress=self.onefile_compress_var.get(), slim_imports=self.slim_var.get(),
            no_docstrings=self.nodoc_var.get(), installer_compression=self._compression_key(),
            close_apps_on_install=self.close_apps_var.get(), warn_on_downgrade=self.warn_downgrade_var.get(),
            obsolete_paths=self._obsolete_paths_list(),
            autostart_with_windows=self.autostart_var.get(),
            hardware=self.hw,
            verify_imports=self.verify_var.get(),
            uninstall_old_versions=self.uninstall_old_var.get(),
            delete_old_dirs=self.delete_old_dirs_var.get(),
            old_version_names=self._old_names_list(),
        )

    def _set_running(self, running: bool) -> None:
        if running:
            self.btn_build.config(state="disabled", text="⏳ ĐANG ĐÓNG GÓI... 0%", bg=Palette.GRAY)
            self.btn_stop.config(state="normal", bg=Palette.RED)
        else:
            self.btn_build.config(state="normal", text=self.IDLE_TEXT, bg=Palette.RED)
            self.btn_stop.config(state="disabled", bg=Palette.SLATE)

    def _start_build(self) -> None:
        if self.pipeline or self.tool_busy:
            return
        if not self.py_info:
            if messagebox.askyesno("Chưa tìm thấy Python",
                                   "Không tự dò được python.exe hợp lệ.\nBạn có muốn chọn thủ công không?", parent=self):
                self._config_python()
            return
        cfg = self.snapshot()
        errors = cfg.validate()
        if errors:
            self._set_status("Chưa thể đóng gói: " + errors[0], "err")
            messagebox.showerror("Chưa thể đóng gói", "\n".join(f"• {e}" for e in errors), parent=self)
            return
        if cfg.make_installer and not os.path.isfile(cfg.iscc_path):
            if not messagebox.askyesno("Không thấy Inno Setup",
                                       "Chưa có đường dẫn ISCC.exe hợp lệ.\nVẫn build nhưng BỎ QUA bước tạo bộ cài?", parent=self):
                return
            cfg.make_installer = False
            self.installer_var.set(False)
        if not self._ensure_stable_names(cfg):   # ver 1.5: tên exe không nên chứa số phiên bản
            self._set_status("Đã huỷ build để sửa tên exe/tên phần mềm (mục 4).", "warn")
            return
        if not self._ensure_product_id(cfg):   # ver 1.5: mã nhận diện sản phẩm cố định
            self._set_status("Đã huỷ build (mã nhận diện sản phẩm).", "warn")
            return
        if not self._ensure_source_version(cfg):   # ver 1.5: VERSION trong mã nguồn phải khớp
            self._set_status("Đã huỷ build (phiên bản trong mã nguồn).", "warn")
            return
        self.version_var.set(cfg.version)
        self.app.persist()

        if not cfg.verify_imports:
            self._launch_pipeline(cfg)
            return
        # ver 1.5 - BƯỚC 0: kiểm tra thư viện trong đúng Python build TRƯỚC khi tốn vài phút biên dịch
        self.btn_build.config(state="disabled", text="⏳ ĐANG KIỂM TRA THƯ VIỆN...", bg=Palette.GRAY)
        self._set_status("Bước 0 - Kiểm tra thư viện mà code cần trong Python dùng để build...", "info")
        self._check_imports(interactive=False, then=lambda report: self._after_precheck(cfg, report))

    def _after_precheck(self, cfg: BuildConfig, report: ImportReport) -> None:
        self._set_running(False)
        if self.pipeline or self.tool_busy:
            return
        if report.error:
            if not messagebox.askyesno("Không kiểm tra được thư viện",
                                       f"{report.error}\n\nVẫn build (KHÔNG kiểm tra thư viện trước/sau)?", parent=self):
                self._set_status("Đã huỷ build.", "warn")
                return
            cfg.import_report = None
            self._launch_pipeline(cfg)
            return
        missing = report.missing()
        if missing:
            answer = messagebox.askyesnocancel(
                "Python build THIẾU thư viện",
                self._missing_text(report) +
                "\n\nNếu build tiếp, exe vẫn 'build thành công' nhưng CHẠY THIẾU tính năng "
                "(đây chính là lỗi NHAN_VIEC v1.6 mất icon khay vì thiếu pystray).\n\n"
                f"• Yes / Có   = Cài ngay ({' '.join(report.pip_packages())}) rồi tự build tiếp\n"
                "• No / Không = Vẫn build (KHÔNG khuyến nghị)\n"
                "• Cancel / Hủy = Dừng lại", icon="warning", parent=self)
            if answer is None:
                self._set_status("Đã huỷ build - còn thiếu thư viện: " + ", ".join(m.name for m in missing), "warn")
                return
            if answer:
                def after_install(ok: bool) -> None:
                    if ok:   # kiểm lại lần nữa rồi mới build (pip "xong" chưa chắc đã đủ)
                        self._start_build()
                self._pip_install(report.pip_packages(), after=after_install)
                return
            self.console.append("> [THƯ VIỆN] Người dùng chọn VẪN BUILD dù thiếu: "
                                + ", ".join(m.name for m in missing) + "\n", "warn")
        cfg.import_report = report
        self._launch_pipeline(cfg)

    def _launch_pipeline(self, cfg: BuildConfig) -> None:
        expected = BuildHistory.expected(cfg.history_key)
        self.progress = ProgressTracker(cfg.compiler, expected)
        self._last_line = ""
        self._last_diagnosis = ""
        self.last_log_path = ""
        self.progressbar["value"] = 0
        self.pct_label.config(text="0%")
        self.elapsed_label.config(text="⏱ 00:00")
        self.eta_label.config(text=f"dự kiến ~{fmt_elapsed(expected['total'])}" if expected else "")
        self._set_bar_color(Palette.BLUE)
        self._set_status(f"Đang khởi động {cfg.compiler} ({cfg.build_mode}, {cfg.effective_jobs} luồng C, "
                         f"chế độ {cfg.perf_mode}) → {cfg.exe_stem}.exe ...", "info")
        self._set_running(True)
        self._start_tick()
        self.console.append(f"\n{'-' * 60}\n> KHỞI TẠO BUILD BẰNG {cfg.compiler.upper()} ({cfg.build_mode}) "
                            f"→ {cfg.exe_stem}.exe  [TURBO: {cfg.perf_mode}, jobs={cfg.effective_jobs}, "
                            f"ưu tiên={PRIORITY_LABELS[cfg.priority_class]}]\n", "info")
        self.pipeline = BuildPipeline(cfg, emit=lambda kind, payload: self.app.dispatch(self._on_event, kind, payload))
        threading.Thread(target=self.pipeline.run, daemon=True, name="build").start()

    def _stop_build(self) -> None:
        if self.pipeline:
            self._set_status("Đang dừng tiến trình đóng gói...", "warn")
            self.console.append("\n[HỆ THỐNG] Đang dừng tiến trình đóng gói...\n", "warn")
            self.pipeline.cancel()

    _ERR_RE = re.compile(r"\b(error|fatal|traceback|exception)\b", re.I)
    _WARN_RE = re.compile(r"\bwarning\b", re.I)

    def _on_event(self, kind: str, payload: object) -> None:
        if kind == "logfile":
            self.last_log_path = str(payload)
            self.console.append(f"> Log lần này: {payload}\n", "info")
        elif kind == "tips":
            for tip in payload:  # type: ignore[union-attr]
                self.console.append(f"[GỢI Ý] {tip}\n", "warn" if str(tip).startswith("⚠") else "info")
        elif kind == "line":
            text = str(payload)
            tag = "err" if self._ERR_RE.search(text) else ("warn" if self._WARN_RE.search(text) else None)
            self.console.append(text, tag)
            if self.progress and self.progress.observe(text, time.monotonic() - self._t0):
                self._apply_progress()
            stripped = text.strip()
            if stripped:
                self._last_line = stripped[:120]
                self._schedule_status_refresh()
        elif kind == "stage":
            value, cap, label, phase = payload  # type: ignore[misc]
            if self.progress:
                self.progress.set_stage(value, cap, label, phase)
                self._apply_progress()
            self._last_line = ""
            self._set_status(label, "info")
            self.console.append(f"\n> {label}\n", "info")
        elif kind == "diagnosis":
            self._last_diagnosis = str(payload)
            self.console.append(f"\n{payload}\n", "warn")
        elif kind == "done":
            self._on_done(payload)

    def _on_done(self, payload: object) -> None:
        ok, message, elapsed, log_path = payload  # type: ignore[misc]
        self._stop_tick()
        if self.progress:
            self.progress.finish(ok)
            self._apply_progress()
        self.elapsed_label.config(text="⏱ " + fmt_elapsed(elapsed))
        self.eta_label.config(text="")
        self._set_bar_color(Palette.GREEN if ok else Palette.RED)
        if log_path:
            self.last_log_path = log_path
        cfg = self.pipeline.cfg if self.pipeline else None
        self.pipeline = None
        self._set_running(False)
        head = "✅ THÀNH CÔNG" if ok else "❌ THẤT BẠI"
        compare = ""
        if cfg and self.progress:
            BuildHistory.record(cfg.history_key, ok, elapsed, self.progress.marks, cfg.effective_jobs, cfg.perf_mode)
            if ok and self.progress.expected_total:
                delta = self.progress.expected_total - elapsed
                if abs(delta) >= 3:
                    compare = (f" · {'nhanh hơn' if delta > 0 else 'chậm hơn'} lần trước {fmt_elapsed(abs(delta))}"
                               f" ({fmt_elapsed(self.progress.expected_total)})")
        self._set_status(f"{head} sau {fmt_elapsed(elapsed)}{compare} · {message}" +
                         (f"  ·  Log: {log_path}" if log_path else ""), "ok" if ok else "err")
        self.console.append(f"\n[{head}] {message}{compare}\n" + (f"[LOG] {log_path}\n" if log_path else ""),
                            "ok" if ok else "err")
        self._schedule_tips()
        if ok:
            if cfg and self.open_done_var.get():
                open_in_explorer(cfg.output_dir)
        else:
            if not self.details_visible:
                self._show_details(True)
            self._show_failure_dialog(message, log_path)

    def _show_failure_dialog(self, message: str, log_path: str) -> None:
        diag_lines = self._last_diagnosis.strip().splitlines()
        short = "\n".join(diag_lines[:9]) + ("\n..." if len(diag_lines) > 9 else "")
        body = message
        if short:
            body += "\n\n" + short
        if log_path:
            body += f"\n\nLog đầy đủ đã ghi tại:\n{log_path}\n\nMở file log ngay?"
            if messagebox.askyesno("Đóng gói thất bại", body, parent=self):
                open_in_explorer(log_path)
        else:
            messagebox.showerror("Đóng gói thất bại", body, parent=self)

    def write_settings(self, s: AppConfig) -> None:
        s.last_script = self.script_var.get().strip()
        s.icon = self.icon_var.get().strip()
        s.compiler = self.compiler_var.get()
        s.nuitka_backend = self._backend_key()
        s.build_mode = self.build_mode_var.get()
        s.console_mode = self.console_mode_var.get()
        s.uac_admin = self.uac_var.get()
        s.clean_build = self.clean_var.get()
        s.lto = self.lto_var.get()
        s.tk_plugin = self.tk_plugin_var.get()
        s.make_installer = self.installer_var.get()
        s.open_when_done = self.open_done_var.get()
        s.details_expanded = self.details_visible
        s.iscc_path = self.iscc_var.get().strip()
        s.company = self.company_var.get().strip()
        s.product = self.product_var.get().strip()
        s.exe_name = self.exe_name_var.get().strip()
        s.version = self.version_var.get().strip()
        s.copyright = self.copyright_var.get().strip()
        s.extra_args = self.extra_var.get()
        s.data_files = [p for k, p in self.data_items if k == "file"]
        s.data_dirs = [p for k, p in self.data_items if k == "dir"]
        # TURBO
        s.perf_mode = self.perf_mode_var.get()
        s.jobs = self._jobs_value()
        s.high_priority = self.priority_var.get()
        s.keep_awake = self.keep_awake_var.get()
        s.power_plan = self.power_plan_var.get()
        s.onefile_compress = self.onefile_compress_var.get()
        s.slim_imports = self.slim_var.get()
        s.no_docstrings = self.nodoc_var.get()
        s.installer_compression = self._compression_key()
        s.close_apps_on_install = self.close_apps_var.get()
        s.warn_on_downgrade = self.warn_downgrade_var.get()
        s.obsolete_paths = self._obsolete_paths_list()
        s.autostart_with_windows = self.autostart_var.get()
        s.verify_imports = self.verify_var.get()
        s.uninstall_old_versions = self.uninstall_old_var.get()
        s.delete_old_dirs = self.delete_old_dirs_var.get()
        s.old_version_names = self._old_names_list()


# ============================================================================
#  TAB 3: BUILD EXE (Visual Studio 2022 Release -> đóng gói bằng Inno Setup)
# ============================================================================
class VsBuilderTab(ttk.Frame):
    """Không biên dịch gì cả - chỉ lấy file .exe (hoặc thư mục Release) mà Visual Studio 2022
    đã xuất ra sau khi bấm Release, rồi đóng gói thành bộ cài .exe bằng Inno Setup (ISCC.exe),
    mặc định dò tại "E:\\Program Files\\Inno Setup 7\\ISCC.exe"."""

    IDLE_TEXT = "📦 TẠO BỘ CÀI (INNO SETUP)"
    COMPRESSION_LABELS = InnoSetupBuilder.COMPRESSION_LABELS
    STATUS_COLORS = BuilderTab.STATUS_COLORS

    def __init__(self, master: tk.Misc, app: "ControlCenterApp"):
        super().__init__(master, padding=(12, 10, 12, 8))
        self.app = app
        s = app.settings
        self.running = False
        self.runner = ProcessRunner()
        self.details_visible = bool(s.vs_details_expanded)
        self.last_installer_path = ""
        self.last_log_path = ""
        self._t0 = 0.0
        self._tick_job: Optional[str] = None
        self.data_items: list[tuple[str, str]] = ([("file", p) for p in s.vs_data_files] +
                                                    [("dir", p) for p in s.vs_data_dirs])

        self.exe_var = tk.StringVar(value=s.vs_exe_path)
        self.icon_var = tk.StringVar(value=s.vs_icon)
        self.company_var = tk.StringVar(value=s.vs_company)
        self.product_var = tk.StringVar(value=s.vs_product)
        self.version_var = tk.StringVar(value=s.vs_version)
        self.copyright_var = tk.StringVar(value=s.vs_copyright)
        self.iscc_var = tk.StringVar(value=s.vs_iscc_path)
        self.comp_label_var = tk.StringVar(
            value=self.COMPRESSION_LABELS.get(s.vs_installer_compression, self.COMPRESSION_LABELS["balanced"]))
        self.close_apps_var = tk.BooleanVar(value=s.vs_close_apps_on_install)
        self.warn_downgrade_var = tk.BooleanVar(value=s.vs_warn_on_downgrade)
        self.autostart_var = tk.BooleanVar(value=s.vs_autostart_with_windows)
        self.arch64_var = tk.BooleanVar(value=s.vs_arch64)
        self.open_done_var = tk.BooleanVar(value=s.vs_open_when_done)
        self.obsolete_paths_text: Optional[tk.Text] = None
        self._obsolete_paths_initial = list(s.vs_obsolete_paths)
        self.status_var = tk.StringVar(value="Sẵn sàng. Chọn file .exe (Release của Visual Studio) rồi bấm nút.")

        self._build_ui()
        self._refresh_data_list()
        self.console.append("> Trạng thái: Sẵn sàng.\n", "ok")
        if not self.iscc_var.get() or not os.path.isfile(self.iscc_var.get()):
            threading.Thread(target=self._auto_detect_iscc, daemon=True, name="vs-detect-iscc").start()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.scroll = ScrollableFrame(self)
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self._build_form(self.scroll.inner)
        self._build_action_bar()

    def _build_form(self, body: ttk.Frame) -> None:
        pad = {"fill": "x", "padx": (0, 6)}
        bold = ("Segoe UI", 9, "bold")

        info = ttk.Label(
            body, foreground="#334155", font=("Segoe UI", 9), justify="left",
            text=("Dùng tab này khi bạn ĐÃ build xong bên Visual Studio 2022 (bấm Release) và chỉ cần "
                  "đóng gói file .exe thành bộ cài chuyên nghiệp bằng Inno Setup - không liên quan gì "
                  "tới Python/Nuitka ở Tab 2."))
        info.pack(pady=(0, 8), **pad)
        info.bind("<Configure>", lambda e: info.configure(wraplength=max(200, e.width - 10)))

        src = ttk.LabelFrame(body, text="1. File .exe (hoặc thư mục Release) từ Visual Studio 2022", padding=8)
        src.pack(pady=(0, 6), **pad)
        row = ttk.Frame(src)
        row.pack(fill="x")
        ttk.Label(row, text="Exe/Thư mục:", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Entry(row, textvariable=self.exe_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="📄 Chọn Exe", command=self._choose_exe).pack(side="left")
        ttk.Button(row, text="📁 Chọn Thư mục", command=self._choose_exe_dir).pack(side="left", padx=(4, 0))
        ttk.Label(src, text=("Chọn 1 file .exe nếu Visual Studio xuất self-contained/single-file, hoặc chọn cả thư mục "
                              "Release (vd bin\\Release\\net8.0-windows) nếu exe còn cần các DLL đi kèm."),
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        res = ttk.LabelFrame(body, text="2. Tài nguyên đính kèm thêm (tuỳ chọn) & Icon bộ cài", padding=8)
        res.pack(pady=6, **pad)
        res.columnconfigure(0, weight=1)
        lst = ttk.Frame(res)
        lst.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=(0, 8))
        self.data_list = tk.Listbox(lst, height=4, font=("Segoe UI", 9), selectmode="extended")
        sb = ttk.Scrollbar(lst, command=self.data_list.yview)
        self.data_list.config(yscrollcommand=sb.set)
        self.data_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Button(res, text="➕ Thêm File", width=18, command=self._add_files).grid(row=0, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="📁 Thêm Thư mục", width=18, command=self._add_dir).grid(row=1, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="❌ Xoá mục đã chọn", width=18, command=self._remove_selected).grid(row=2, column=1, sticky="ew", pady=1)
        ttk.Button(res, text="🎨 Chọn Icon (.ico)", width=18, command=self._choose_icon).grid(row=3, column=1, sticky="ew", pady=1)
        ttk.Label(res, textvariable=self.icon_var, foreground="gray", font=("Segoe UI", 8)).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(res, text="(chỉ dùng làm icon bộ cài - icon của file .exe do chính project Visual Studio quyết định)",
                  foreground="gray", font=("Segoe UI", 8)).grid(row=5, column=0, columnspan=2, sticky="w")

        meta = ttk.LabelFrame(body, text="3. Siêu dữ liệu (Metadata bản quyền)", padding=8)
        meta.pack(pady=6, **pad)
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(3, weight=1)
        rows = (("Tên cơ quan:", self.company_var, 0, 0), ("Tên phần mềm:", self.product_var, 0, 2),
                ("Phiên bản (x.x.x.x):", self.version_var, 1, 0), ("Bản quyền:", self.copyright_var, 1, 2))
        for label, var, r, c in rows:
            ttk.Label(meta, text=label).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 14, 0), pady=2)
            ttk.Entry(meta, textvariable=var).grid(row=r, column=c + 1, sticky="ew", padx=5, pady=2)
        ttk.Checkbutton(meta, text="Bộ cài 64-bit (ArchitecturesInstallIn64BitMode)", variable=self.arch64_var
                        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        opt = ttk.LabelFrame(body, text="4. Nén bộ cài & Nâng cấp / Dọn bản cũ (Inno Setup)", padding=8)
        opt.pack(pady=6, **pad)
        opt.columnconfigure(1, weight=1)
        ttk.Label(opt, text="Nén bộ cài:", font=bold).grid(row=0, column=0, sticky="w", pady=2)
        self.comp_box = ttk.Combobox(opt, textvariable=self.comp_label_var,
                                     values=list(self.COMPRESSION_LABELS.values()), state="readonly", width=40)
        self.comp_box.grid(row=0, column=1, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(opt, text="Tự đóng app đang chạy trước khi cài đè", variable=self.close_apps_var
                        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=1)
        ttk.Checkbutton(opt, text="Cảnh báo/chặn khi cài đè bằng bản CŨ HƠN bản đang có trên máy", variable=self.warn_downgrade_var
                        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=1)
        ttk.Checkbutton(opt, text="Tự khởi động cùng Windows (tuỳ chọn lúc cài đặt, mặc định KHÔNG tick)",
                         variable=self.autostart_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=1)
        ttk.Label(opt, text="Cờ này KHÔNG bắt buộc - chỉ bật nếu phần mềm cần chạy nền/tự mở khi đăng nhập Windows.",
                  foreground="gray", font=("Segoe UI", 8)).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(opt, text="File/thư mục dư từ bản cũ cần xoá trước khi cài (mỗi dòng 1 đường dẫn, tính từ thư mục cài đặt):",
                  foreground="gray", font=("Segoe UI", 8)).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 2))
        obs_frame = ttk.Frame(opt)
        obs_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.obsolete_paths_text = tk.Text(obs_frame, height=3, font=("Consolas", 9))
        self.obsolete_paths_text.pack(side="left", fill="both", expand=True)
        obs_sb = ttk.Scrollbar(obs_frame, command=self.obsolete_paths_text.yview)
        self.obsolete_paths_text.config(yscrollcommand=obs_sb.set)
        obs_sb.pack(side="right", fill="y")
        if self._obsolete_paths_initial:
            self.obsolete_paths_text.insert("1.0", "\n".join(self._obsolete_paths_initial))

        tool = ttk.LabelFrame(body, text="5. Inno Setup 7", padding=8)
        tool.pack(pady=(6, 8), **pad)
        row_iscc = ttk.Frame(tool)
        row_iscc.pack(fill="x")
        ttk.Label(row_iscc, text="Đường dẫn ISCC.exe:", font=bold).pack(side="left")
        ttk.Entry(row_iscc, textvariable=self.iscc_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row_iscc, text="📁 Chọn ISCC", command=self._choose_iscc).pack(side="left")
        ttk.Button(row_iscc, text="↻ Dò lại", command=self._redetect_iscc).pack(side="left", padx=(4, 0))
        ttk.Label(tool, text=r'Mặc định: E:\Program Files\Inno Setup 7\ISCC.exe (được tự dò khi mở tool, có thể sửa tay).',
                  foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(tool, text="Mở thư mục bộ cài khi xong", variable=self.open_done_var).pack(anchor="w", pady=(4, 0))

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self, padding=(0, 6, 0, 0))
        bar.grid(row=1, column=0, sticky="ew")
        ttk.Separator(bar).pack(fill="x", pady=(0, 8))

        row_btn = ttk.Frame(bar)
        row_btn.pack(fill="x")
        self.btn_build = color_button(row_btn, self.IDLE_TEXT, Palette.RED, self._start_build)
        self.btn_build.config(font=("Segoe UI", 12, "bold"), pady=8)
        self.btn_build.pack(side="left", fill="x", expand=True)
        self.btn_stop = color_button(row_btn, "⛔ Dừng", Palette.SLATE, self._stop_build, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        color_button(row_btn, "📂 Mở bộ cài", Palette.BLUE, self._open_output).pack(side="left", padx=(8, 0))
        self.btn_details = ttk.Button(row_btn, text="▸ Chi tiết", width=10, command=self._toggle_details)
        self.btn_details.pack(side="left", padx=(8, 0))

        self.status_label = ttk.Label(bar, textvariable=self.status_var, anchor="w",
                                      foreground=self.STATUS_COLORS["info"], font=("Segoe UI", 9))
        self.status_label.pack(fill="x", pady=(8, 4))
        self.status_label.bind("<Configure>", lambda e: self.status_label.configure(wraplength=max(200, e.width - 10)))

        self.details_frame = ttk.LabelFrame(bar, text="Nhật ký ISCC", padding=4)
        self.console = ConsoleText(self.details_frame, bg="#0f172a", fg="#e2e8f0", height=9)
        self.console.pack(fill="both", expand=True)
        if self.details_visible:
            self._show_details(True)

    # ---------------- tiện ích nhỏ ----------------
    def _set_status(self, text: str, kind: str = "info") -> None:
        self.status_var.set(text)
        self.status_label.configure(foreground=self.STATUS_COLORS.get(kind, self.STATUS_COLORS["info"]))

    def _toggle_details(self) -> None:
        self._show_details(not self.details_visible)

    def _show_details(self, show: bool) -> None:
        self.details_visible = show
        if show:
            self.details_frame.pack(fill="both", expand=True, pady=(0, 4))
            self.btn_details.config(text="▾ Chi tiết")
        else:
            self.details_frame.pack_forget()
            self.btn_details.config(text="▸ Chi tiết")

    def _refresh_data_list(self) -> None:
        self.data_list.delete(0, "end")
        for kind, path in self.data_items:
            self.data_list.insert("end", ("📁 " if kind == "dir" else "📄 ") + path)

    def _add_files(self) -> None:
        for f in filedialog.askopenfilenames(title="Chọn file đính kèm thêm", parent=self):
            if ("file", f) not in self.data_items:
                self.data_items.append(("file", f))
        self._refresh_data_list()

    def _add_dir(self) -> None:
        d = filedialog.askdirectory(title="Chọn thư mục đính kèm thêm", parent=self)
        if d and ("dir", d) not in self.data_items:
            self.data_items.append(("dir", d))
            self._refresh_data_list()

    def _remove_selected(self) -> None:
        for idx in sorted(self.data_list.curselection(), reverse=True):
            del self.data_items[idx]
        self._refresh_data_list()

    def _choose_exe(self) -> None:
        path = filedialog.askopenfilename(title="Chọn file .exe (Release Visual Studio)",
                                          filetypes=[("Chương trình", "*.exe"), ("Tất cả", "*.*")], parent=self)
        if path:
            self.exe_var.set(path)

    def _choose_exe_dir(self) -> None:
        d = filedialog.askdirectory(title="Chọn thư mục Release (chứa .exe + DLL phụ thuộc)", parent=self)
        if d:
            self.exe_var.set(d)

    def _choose_icon(self) -> None:
        path = filedialog.askopenfilename(title="Chọn Icon", filetypes=[("Icon", "*.ico")], parent=self)
        if path:
            self.icon_var.set(path)

    def _choose_iscc(self) -> None:
        path = filedialog.askopenfilename(title="Chọn file ISCC.exe",
                                          filetypes=[("ISCC", "ISCC.exe"), ("Tất cả", "*.*")], parent=self)
        if path:
            self.iscc_var.set(path)

    def _redetect_iscc(self) -> None:
        self.iscc_var.set("")
        threading.Thread(target=self._auto_detect_iscc, daemon=True, name="vs-detect-iscc").start()

    def _auto_detect_iscc(self) -> None:
        found = IsccLocator.find("")
        if found:
            self.app.dispatch(self.iscc_var.set, found)
            self.app.dispatch(self.console.append, f"> Đã tự tìm thấy ISCC: {found}\n", "ok")
        else:
            default_guess = r"E:\Program Files\Inno Setup 7\ISCC.exe"
            if os.path.isfile(default_guess):
                self.app.dispatch(self.iscc_var.set, default_guess)

    def _open_output(self) -> None:
        if self.last_installer_path and os.path.isfile(self.last_installer_path):
            open_in_explorer(self.last_installer_path)
            return
        exe = self.exe_var.get().strip()
        if not exe:
            messagebox.showinfo("Chưa chọn file", "Hãy chọn file .exe (hoặc thư mục Release) trước.", parent=self)
            return
        cfg = self._snapshot()
        open_in_explorer(cfg.installer_dir if os.path.isdir(cfg.installer_dir) else cfg.base_dir)

    def _compression_key(self) -> str:
        return next((k for k, v in self.COMPRESSION_LABELS.items() if v == self.comp_label_var.get()), "balanced")

    def _obsolete_paths_list(self) -> list[str]:
        if self.obsolete_paths_text is None:
            return []
        raw = self.obsolete_paths_text.get("1.0", "end")
        return [line.strip().strip("/\\") for line in raw.splitlines() if line.strip()]

    # ---------------- build ----------------
    def _snapshot(self) -> VsPackageConfig:
        return VsPackageConfig(
            exe_path=self.exe_var.get().strip(), icon=self.icon_var.get().strip(),
            company=self.company_var.get().strip(), product=self.product_var.get().strip(),
            version=normalize_version(self.version_var.get()), copyright=self.copyright_var.get().strip(),
            iscc_path=self.iscc_var.get().strip(), installer_compression=self._compression_key(),
            close_apps_on_install=self.close_apps_var.get(), warn_on_downgrade=self.warn_downgrade_var.get(),
            autostart_with_windows=self.autostart_var.get(), obsolete_paths=self._obsolete_paths_list(),
            data_files=[p for k, p in self.data_items if k == "file"],
            data_dirs=[p for k, p in self.data_items if k == "dir"],
            arch64=self.arch64_var.get(),
        )

    def _set_running(self, running: bool) -> None:
        self.running = running
        if running:
            self.btn_build.config(state="disabled", text="⏳ ĐANG TẠO BỘ CÀI...", bg=Palette.GRAY)
            self.btn_stop.config(state="normal", bg=Palette.RED)
        else:
            self.btn_build.config(state="normal", text=self.IDLE_TEXT, bg=Palette.RED)
            self.btn_stop.config(state="disabled", bg=Palette.SLATE)

    def _start_build(self) -> None:
        if self.running:
            return
        cfg = self._snapshot()
        errors = cfg.validate()
        if errors:
            messagebox.showerror("Thiếu thông tin", "\n".join(errors), parent=self)
            return
        self.console.clear()
        self._set_status("Đang tạo bộ cài bằng Inno Setup...", "info")
        self._set_running(True)
        if not self.details_visible:
            self._show_details(True)
        self._t0 = time.monotonic()
        self.runner = ProcessRunner()
        threading.Thread(target=self._run_build, args=(cfg,), daemon=True, name="vs-iscc-build").start()

    def _stop_build(self) -> None:
        if self.running:
            self.runner.terminate()
            self._set_status("Đang dừng...", "warn")

    def _run_build(self, cfg: VsPackageConfig) -> None:
        ok, message = False, ""
        try:
            os.makedirs(cfg.work_dir, exist_ok=True)
            os.makedirs(cfg.installer_dir, exist_ok=True)
            extra = InnoSetupBuilder.extra_files_block(cfg.data_files, cfg.data_dirs)
            builder = InnoSetupBuilder(cfg.iscc_path, self.runner)

            def on_line(line: str) -> None:
                self.app.dispatch(self.console.append, line)

            self.app.dispatch(self.console.append,
                              f"> Đóng gói: {cfg.exe_path}\n> Sản phẩm: {cfg.product} v{cfg.version}\n", "info")
            ok, message = builder.build(cfg, cfg.exe_path, on_line, priority="above_normal", extra_files=extra)
        except Exception as exc:  # noqa: BLE001
            message = f"Lỗi: {exc}"
            log.exception("Lỗi khi tạo bộ cài Tab 3")
        elapsed = time.monotonic() - self._t0
        self.app.dispatch(self._on_done, cfg, ok, message, elapsed)

    def _on_done(self, cfg: VsPackageConfig, ok: bool, message: str, elapsed: float) -> None:
        self._set_running(False)
        head = "✅ THÀNH CÔNG" if ok else "❌ THẤT BẠI"
        self._set_status(f"{head} sau {fmt_elapsed(elapsed)} · {message}", "ok" if ok else "err")
        self.console.append(f"\n[{head}] {message}\n", "ok" if ok else "err")
        if ok:
            self.last_installer_path = message
            try:
                os.makedirs(os.path.join(cfg.base_dir, "installer_logs"), exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = os.path.join(cfg.base_dir, "installer_logs", f"vsbuild_{stamp}.log")
                Path(log_path).write_text(self.console.content(), encoding="utf-8")
                self.last_log_path = log_path
            except OSError:
                pass
            if self.open_done_var.get():
                open_in_explorer(cfg.installer_dir)
        else:
            messagebox.showerror("Tạo bộ cài thất bại", message, parent=self)

    def write_settings(self, s: AppConfig) -> None:
        s.vs_exe_path = self.exe_var.get().strip()
        s.vs_icon = self.icon_var.get().strip()
        s.vs_company = self.company_var.get().strip()
        s.vs_product = self.product_var.get().strip()
        s.vs_version = self.version_var.get().strip()
        s.vs_copyright = self.copyright_var.get().strip()
        s.vs_iscc_path = self.iscc_var.get().strip()
        s.vs_installer_compression = self._compression_key()
        s.vs_close_apps_on_install = self.close_apps_var.get()
        s.vs_warn_on_downgrade = self.warn_downgrade_var.get()
        s.vs_autostart_with_windows = self.autostart_var.get()
        s.vs_obsolete_paths = self._obsolete_paths_list()
        s.vs_data_files = [p for k, p in self.data_items if k == "file"]
        s.vs_data_dirs = [p for k, p in self.data_items if k == "dir"]
        s.vs_arch64 = self.arch64_var.get()
        s.vs_open_when_done = self.open_done_var.get()
        s.vs_details_expanded = self.details_visible


# ============================================================================
#  CỬA SỔ CHÍNH
# ============================================================================
class ControlCenterApp(tk.Tk):
    def __init__(self, settings: AppConfig):
        super().__init__()
        # LƯU Ý: không đặt tên thuộc tính là self.config vì Tk đã có phương thức config()
        self.settings = settings
        self.title(f"{APP_TITLE}  |  v{APP_VERSION} TURBO (ver 1.5)")
        self.geometry("1040x800")
        self.minsize(880, 560)
        if IS_WINDOWS:
            duong_dan_icon = _duong_dan_tai_nguyen("tools.ico")
            if duong_dan_icon:
                try:
                    self.iconbitmap(duong_dan_icon)
                except Exception:
                    pass
        self._apply_style()
        self.dispatcher = MainThreadDispatcher(self)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        self.analyzer = AnalyzerTab(nb, self)
        self.builder = BuilderTab(nb, self)
        self.vs_builder = VsBuilderTab(nb, self)
        nb.add(self.analyzer, text="  1. Phân Tích Log & Đề Xuất  ")
        nb.add(self.builder, text="  2. BUILD PYTHON  ")
        nb.add(self.vs_builder, text="  3. Build EXE (Visual Studio + Inno Setup)  ")

        ttk.Label(self, text="© 2026 Bản quyền thuộc về Mã Đức Hiển - All Rights Reserved",
                  font=("Segoe UI", 9, "italic"), foreground="gray").pack(side="bottom", pady=4)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook.Tab", padding=(12, 6), font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Build.Horizontal.TProgressbar", thickness=18, troughcolor="#e2e8f0",
                        bordercolor="#cbd5e1", background=Palette.BLUE, lightcolor=Palette.BLUE, darkcolor=Palette.BLUE)
        self.option_add("*Font", ("Segoe UI", 10))

    def dispatch(self, fn: Callable, *args, **kwargs) -> None:
        self.dispatcher.call(fn, *args, **kwargs)

    def persist(self) -> None:
        self.analyzer.write_settings(self.settings)
        self.builder.write_settings(self.settings)
        self.vs_builder.write_settings(self.settings)
        self.settings.save()

    def _on_close(self) -> None:
        if self.builder.pipeline:
            if not messagebox.askyesno("Đang đóng gói", "Tiến trình đóng gói đang chạy. Dừng và thoát?", parent=self):
                return
            self.builder.pipeline.cancel()
        if self.vs_builder.running:
            if not messagebox.askyesno("Đang tạo bộ cài", "Inno Setup đang chạy ở Tab 3. Dừng và thoát?", parent=self):
                return
            self.vs_builder.runner.terminate()
        self.analyzer.cancel_event.set()
        self.persist()
        self.destroy()


def main() -> None:
    enable_high_dpi()
    setup_logging()
    log.info("Khởi động Control Center v%s (frozen=%s, python=%s)", APP_VERSION, is_frozen(), sys.executable)
    app = ControlCenterApp(AppConfig.load())
    app.mainloop()


if __name__ == "__main__":
    main()
