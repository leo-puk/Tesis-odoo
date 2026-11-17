"""Casuisticas: de un log de Odoo a eventos clasificados, y de un diff humano a hunks.

Dos catalogos de reglas, ambos para el salto 16.0 -> 17.0:

- RULES   clasifica un evento del log (sintoma) en una categoria de la taxonomia.
- GUIDE17 etiqueta un hunk del [MIG] humano con la tarea de la guia OCA
          "Migration to version 17.0" que lo explica; un hunk sin etiqueta cae en
          "Do the rest of the changes" (etiqueta R del protocolo).

Las reglas son una primera pasada automatica: la categoria y la etiqueta finales de
cada casuistica las fija el codificador humano al registrarla.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------- taxonomia
CATEGORIES = {
    "A": "manifest y dependencias",
    "B": "API Python",
    "C": "modelo y ORM",
    "D": "vistas",
    "E": "datos XML/CSV y seguridad",
    "F": "frontend JS/OWL",
    "G": "reportes QWeb",
    "H": "migracion de datos",
    "I": "ecosistema (dependencias externas)",
    "J": "pruebas",
    "K": "ruido",
    "?": "sin clasificar",
}

# Etiqueta de cobertura del estandar (seccion 2 del protocolo).
COVERAGE = {
    "L": "listada en la guia OCA de la version",
    "A": "la resuelve una herramienta automatica (odoo-module-migrator / views_migration_17)",
    "U": "la cubre OpenUpgrade (upgrade_analysis + scripts)",
    "C": "la atrapa la CI (pre-commit o pruebas del modulo)",
    "V": "solo la detecta la verificacion manual recomendada por Odoo",
    "R": "ninguna pieza del estandar la anticipa ('Do the rest of the changes')",
    "S": "silenciosa: pasa todo y solo la ve el oraculo diferencial o un [FIX] posterior",
}

# ------------------------------------------------------- eventos del log
# 2026-09-21 20:50:26,984 15 ERROR <db> <logger>: <mensaje>
HEAD_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) \d+ "
                     r"(CRITICAL|ERROR|WARNING|INFO|DEBUG) (\S+) ([\w.]+): ?(.*)$")
LEVELS = ("CRITICAL", "ERROR", "WARNING")
FRAME_RE = re.compile(r'File "(/mnt/extra-addons/[^"]+)", line (\d+)')
XMLFILE_RE = re.compile(r"(/mnt/extra-addons/[^\s:'\"]+\.(?:xml|csv))(?::(\d+))?")


@dataclass
class Event:
    level: str
    logger: str
    message: str               # primera linea
    detail: str = ""           # continuacion (traceback, contexto del ParseError)
    line_no: int = 0           # linea del log
    location: str = ""         # archivo:linea dentro de /mnt/extra-addons, si se puede
    signature: str = ""
    category: str = "?"
    rule: str = ""
    guide: str = ""

    def dict(self):
        return asdict(self)


_NORMALIZERS = [
    (re.compile(r"/mnt/extra-addons/"), ""),
    (re.compile(r"filestore/[^/\s']+/"), "filestore/DB/"),   # BD de linea base != BD de corrida
    (re.compile(r"0x[0-9a-f]+"), "0xH"),
    (re.compile(r"\b[0-9a-f]{12,40}\b"), "H"),
    (re.compile(r"\d+"), "N"),
    (re.compile(r"\s+"), " "),
]


def normalize(text: str) -> str:
    for rx, rep in _NORMALIZERS:
        text = rx.sub(rep, text)
    return text.strip()[:300]


def _exception_line(detail: str) -> str:
    """Linea 'Tipo: mensaje' de la causa raiz.

    En una cadena ("The above exception was the direct cause of...") la primera
    excepcion es la raiz; las siguientes la envuelven ("invalid manifest",
    "Failed to load registry") y darian la misma firma a casuisticas distintas.
    """
    for ln in detail.splitlines():
        if re.match(r"^[\w.]+(Error|Exception|Warning|Violation)\b.*", ln):
            return ln.strip()
    return ""


def parse_log(text: str, min_level: str = "WARNING") -> list[Event]:
    keep = LEVELS[:LEVELS.index(min_level) + 1]
    events: list[Event] = []
    cur: Event | None = None
    orphan: list[str] = []          # traceback impreso fuera del logger (crash de arranque)
    for i, ln in enumerate(text.splitlines(), 1):
        m = HEAD_RE.match(ln)
        if m:
            if orphan:
                events.append(Event("CRITICAL", "stderr", orphan[-1], "\n".join(orphan), i))
                orphan = []
            _, lvl, _db, logger, msg = m.groups()
            cur = Event(lvl, logger, msg, "", i) if lvl in keep else None
            if cur:
                events.append(cur)
        elif cur is not None:
            cur.detail += ln + "\n"
        elif ln.startswith("Traceback") or orphan:
            orphan.append(ln)
    if orphan:
        events.append(Event("CRITICAL", "stderr", orphan[-1], "\n".join(orphan), 0))

    for e in events:
        exc = _exception_line(e.detail)
        frames = FRAME_RE.findall(e.detail)
        xml = XMLFILE_RE.search(e.message + "\n" + e.detail)
        if frames:
            e.location = f"{frames[-1][0].replace('/mnt/extra-addons/', '')}:{frames[-1][1]}"
        elif xml:
            e.location = xml.group(1).replace("/mnt/extra-addons/", "") + (
                f":{xml.group(2)}" if xml.group(2) else "")
        e.signature = f"{e.level}|{e.logger}|{normalize(exc or e.message)}"
        classify(e)
    return events


def sig_id(signature: str) -> str:
    return hashlib.sha1(signature.encode()).hexdigest()[:10]


# ------------------------------------------------------- reglas de sintoma
# (id, regex sobre mensaje+detalle, categoria, tarea de la guia o "")
RULES: list[tuple[str, str, str, str]] = [
    ("attrs_states", r'"attrs" and "states" attributes are no longer used|attrs.*no longer used', "D", "G17-07"),
    ("active_id_ctx", r"\bactive_(id|ids|model)\b.*(deprecated|context)", "D", "G17-06"),
    ("xpath_missing", r"cannot be located in parent view|Element .* cannot be located", "D", ""),
    ("view_field_missing", r'Field [`"\']?\w+[`"\']? does not exist in model|Field "\w+" does not exist', "D", ""),
    ("view_invalid", r"Invalid view|Error while validating view|invalid view definition", "D", ""),
    ("settings_view", r"res\.config\.settings|app_settings_block|o_setting_box", "D", "G17-10"),
    ("hook_signature", r"_(init|uninstall)_hook\(\) (takes|missing)", "B", "G17-04"),
    ("get_resource_path", r"get_resource_path", "B", "G17-05"),
    ("name_get", r"\bname_get\b", "B", "G17-03"),
    ("import_error", r"\b(ImportError|ModuleNotFoundError)\b", "B", ""),
    ("attribute_error", r"\bAttributeError\b", "B", ""),
    ("type_error_sig", r"\bTypeError\b.*(argument|positional|keyword)", "B", ""),
    ("deprecation", r"DeprecationWarning|is deprecated", "B", ""),
    ("unknown_field_orm", r"KeyError: '\w+'|Invalid field '?\w+'? on model|unknown field", "C", ""),
    ("compute_depends", r"depends on non-stored|Field \S+ cannot be computed|invalid depends", "C", ""),
    ("selection", r"selection|not a valid value for field", "C", ""),
    ("xmlid_missing", r"External ID not found in the system", "E", ""),
    ("access_csv", r"ir\.model\.access|No matching record found for external id .* in field 'Model'", "E", ""),
    ("parse_error", r"\bParseError\b|while parsing", "E", ""),
    ("owl_template", r"owl=\"1\"|OwlError|Missing template", "F", "G17-12"),
    ("assets", r"assets|\.js:|Could not get content for", "F", ""),
    ("qweb_report", r"QWebException|report_\w+|t-esc", "G", ""),
    ("db_not_null", r"NotNullViolation|unable to set NOT NULL", "H", ""),
    ("db_fk", r"ForeignKeyViolation|violates foreign key", "H", ""),
    ("db_unique", r"UniqueViolation|duplicate key value", "H", ""),
    ("db_column", r"column \S+ does not exist|UndefinedColumn", "H", ""),
    ("openupgrade", r"OpenUpgrade|openupgrade", "H", ""),
    ("unmet_deps", r"unmet dependenc|depends on .* not (found|available)|not installable", "A", ""),
    ("manifest_version", r"Invalid version|version .*(invalid|does not match)|incompatible version", "A", "G17-01"),
    ("manifest_invalid", r"invalid manifest", "A", ""),
    ("ext_dependency", r"external dependency|No module named|python dependency", "I", ""),
    ("blocked_requests", r"external requests|BlockedRequest|Requests are not allowed", "J", "G17-11"),
    ("test_fail", r"^(FAIL|ERROR): test_|odoo\.addons\.\w+\.tests\.|failed, \d+ error", "J", ""),
    ("noise_same_label", r"have the same label", "K", ""),
    ("noise_column_drop", r"Not dropping the column", "K", ""),
]
_RULES_RX = [(rid, re.compile(rx, re.I | re.M), cat, g) for rid, rx, cat, g in RULES]


def classify(e: Event) -> Event:
    text = e.message + "\n" + e.detail
    for rid, rx, cat, guide in _RULES_RX:
        if rx.search(text):
            e.rule, e.category, e.guide = rid, cat, guide
            break
    return e


# --------------------------------------------- guia OCA 17.0 sobre los hunks
# Tareas de https://github.com/OCA/maintainer-tools/wiki/Migration-to-version-17.0
GUIDE17_TASKS = {
    "G17-01": "bump version a 17.0.1.0.0",
    "G17-02": "eliminar carpeta migrations",
    "G17-03": "name_get -> _compute_display_name",
    "G17-04": "hooks reciben env",
    "G17-05": "get_resource_path -> file_path",
    "G17-06": "active_id/active_model en contexto de vistas",
    "G17-07": "attrs/states -> expresiones python",
    "G17-08": "readonly en la vista y no en el modelo",
    "G17-09": "invisible -> column_invisible en tree",
    "G17-10": "vistas de settings simplificadas",
    "G17-11": "mockear requests en tests",
    "G17-12": "quitar owl=\"1\"",
    "G17-13": "agregar tests",
    "G17-14": "BaseCommon en tests",
}
# (tarea, archivo regex o None, regex sobre lineas quitadas, regex sobre lineas agregadas)
GUIDE17: list[tuple[str, str | None, str | None, str | None]] = [
    ("G17-01", r"__manifest__\.py$", r'"version"', r'"version":\s*"17\.0'),
    ("G17-02", r"/migrations/", r".", None),
    ("G17-03", None, r"\bname_get\b", r"_compute_display_name"),
    ("G17-04", None, r"def \w*_hook\(\s*cr\b|def \w*_hook\(\s*cr, *registry", r"def \w*_hook\(\s*env"),
    ("G17-05", None, r"get_resource_path", r"file_path"),
    ("G17-06", r"\.xml$", r"\bactive_(id|ids|model)\b", None),
    ("G17-07", r"\.xml$", r"\b(attrs|states)=", r"\b(invisible|readonly|required)="),
    ("G17-09", r"\.xml$", None, r"column_invisible"),
    ("G17-10", r"\.xml$", r"app_settings_block|o_settings_container|o_setting_box", r"<(app|block|setting)\b"),
    ("G17-11", r"tests/", None, r"requests|mock"),
    ("G17-12", r"\.xml$", r'owl="1"', None),
    ("G17-14", r"tests/", None, r"BaseCommon"),
    ("G17-13", r"tests/test_\w+\.py$", None, r"def test_"),
]
# Cambios administrativos que la guia pide o que genera el tooling (no son migracion)
ADMIN_FILES = re.compile(r"(README\.rst|readme/|static/description/|i18n/|\.pot$|"
                         r"setup/|pyproject\.toml|\.pre-commit|LICENSE)")


# Reescrituras que pide pre-commit/pylint-odoo y no cambian comportamiento.
_STYLE = [(re.compile(r"super\(\s*\w+\s*,\s*\w+\s*\)"), "super()"),
          (re.compile(r"<\?xml[^>]*\?>"), ""),
          (re.compile(r"[\s'\",]"), "")]


def _style_norm(lines: list[str]) -> str:
    s = "".join(lines)
    for rx, rep in _STYLE:
        s = rx.sub(rep, s)
    return s


def tag_hunk(path: str, removed: list[str], added: list[str]) -> list[str]:
    if ADMIN_FILES.search(path):
        return ["ADMIN"]
    if _style_norm(removed) == _style_norm(added):
        return ["ESTILO"]
    rem, add = "\n".join(removed), "\n".join(added)
    tags = []
    for task, frx, rrx, arx in GUIDE17:
        if frx and not re.search(frx, path):
            continue
        hit_r = bool(rrx and re.search(rrx, rem))
        hit_a = bool(arx and re.search(arx, add))
        if (rrx and arx and (hit_r or hit_a)) or (rrx and not arx and hit_r) or (arx and not rrx and hit_a):
            tags.append(task)
    if not tags and not rem.strip() and not add.strip():
        tags.append("ADMIN")        # solo espacios / modo de archivo
    return tags or ["SIN_GUIA"]


# ---------------------------------------------------------- hunks de un diff
@dataclass
class Hunk:
    id: int
    path: str                      # ruta dentro del repo (modulo/...)
    status: str                    # M | A | D | B (binario)
    header: str                    # @@ -a,b +c,d @@ contexto
    patch: str                     # parche autocontenido (cabecera de archivo + hunk)
    removed: int = 0
    added: int = 0
    tags: list[str] = field(default_factory=list)
    state: str = "pending"         # pending | applied
    commit: str = ""
    casuistics: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("patch")
        return d


def split_diff(diff: str) -> list[Hunk]:
    """Parte un `git diff --no-renames` en hunks aplicables por separado.

    Un archivo nuevo, borrado o binario es un solo hunk (no tiene sentido partirlo).
    """
    hunks: list[Hunk] = []
    files = re.split(r"(?m)^(?=diff --git )", diff)
    for fd in files:
        if not fd.startswith("diff --git "):
            continue
        m = re.match(r"diff --git a/(\S+) b/(\S+)", fd)
        path = m.group(2) if m else "?"
        head, sep, body = fd.partition("\n@@")
        if "Binary files" in fd or "GIT binary patch" in fd:
            hunks.append(Hunk(len(hunks) + 1, path, "B", "binario", fd))
            continue
        status = "A" if "\nnew file mode" in head else "D" if "\ndeleted file mode" in head else "M"
        if not sep:                                   # solo cambio de modo
            hunks.append(Hunk(len(hunks) + 1, path, status, "modo", fd, tags=["ADMIN"]))
            continue
        parts = ["@@" + p for p in ("\n@@" + body).split("\n@@")[1:]]
        if status in ("A", "D"):
            parts = ["\n".join(parts)]
        for p in parts:
            lines = p.splitlines()
            rem = [ln[1:] for ln in lines[1:] if ln.startswith("-")]
            add = [ln[1:] for ln in lines[1:] if ln.startswith("+")]
            patch = head.rstrip("\n") + "\n" + p.rstrip("\n") + "\n"
            h = Hunk(len(hunks) + 1, path, status, lines[0][:160], patch,
                     removed=len(rem), added=len(add))
            h.tags = tag_hunk(path, rem, add)
            hunks.append(h)
    return hunks
