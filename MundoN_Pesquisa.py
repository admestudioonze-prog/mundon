import csv
import os
import shutil
import sqlite3
import sys
import tempfile
import webbrowser
from datetime import datetime
from html import escape
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "MundoN Pesquisa"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = app_dir()
DB_DIR = os.path.join(BASE_DIR, "databases")
os.makedirs(DB_DIR, exist_ok=True)

COLUMNS = [
    ("id", "ID"),
    ("status", "Status"),
    ("manchete", "Manchete"),
    ("data_da_publicacao", "Data"),
    ("cidade", "Cidade"),
    ("categoria", "Categoria"),
]

ALL_FIELDS = [
    "id", "status", "manchete", "credito_imagem", "imagem_principal", "resumo", "paragrafo",
    "mostrar_galeria", "galeria_de_midia", "data_da_publicacao", "updated_date", "cidade",
    "destaque_home", "categoria", "carrossel", "posicao", "materias_individuais", "mundo_pet_tv",
    "publish_date", "unpublish_date", "conteudo_texto"
]


def list_databases():
    return sorted([f for f in os.listdir(DB_DIR) if f.lower().endswith((".sqlite", ".db"))])


def unique_dest_name(filename):
    base, ext = os.path.splitext(os.path.basename(filename))
    candidate = base + ext
    i = 2
    while os.path.exists(os.path.join(DB_DIR, candidate)):
        candidate = f"{base}_{i}{ext}"
        i += 1
    return candidate


def get_conn(dbname):
    return sqlite3.connect(os.path.join(DB_DIR, dbname))


def safe_get(row, key):
    try:
        val = row[key]
    except Exception:
        return ""
    return "" if val is None else str(val)


class MundoNApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1280x780")
        self.minsize(1100, 680)

        self.results = []
        self.selected_record = None
        self.db_var = tk.StringVar(value="Todos os bancos")
        self.query_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Todos")
        self.city_var = tk.StringVar(value="Todas")
        self.category_var = tk.StringVar(value="Todas")
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()

        self._style()
        self._build_ui()
        self.refresh_databases()
        self.populate_filters()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f1f5f9")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", background="#f1f5f9", foreground="#0f172a", font=("Arial", 24, "bold"))
        style.configure("Sub.TLabel", background="#f1f5f9", foreground="#475569", font=("Arial", 11))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial", 14, "bold"))
        style.configure("Text.TLabel", background="#ffffff", foreground="#334155", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10), padding=8)
        style.configure("Primary.TButton", font=("Arial", 10, "bold"), padding=8)
        style.configure("Treeview", rowheight=30, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    def _build_ui(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 14))

        left_header = ttk.Frame(header)
        left_header.pack(side="left", fill="x", expand=True)
        ttk.Label(left_header, text="Pesquisa de matérias", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left_header, text="Consulta offline em múltiplos bancos SQLite, sem alterar os bancos atuais.", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        btns = ttk.Frame(header)
        btns.pack(side="right")
        ttk.Button(btns, text="Adicionar banco", command=self.add_database).pack(side="left", padx=4)
        ttk.Button(btns, text="Exportar CSV", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpar filtros", command=self.clear_filters).pack(side="left", padx=4)

        filters = ttk.Frame(root, padding=14, style="Card.TFrame")
        filters.pack(fill="x", pady=(0, 14))

        ttk.Label(filters, text="Banco", background="#ffffff").grid(row=0, column=0, sticky="w")
        self.db_combo = ttk.Combobox(filters, textvariable=self.db_var, state="readonly", width=28)
        self.db_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.db_combo.bind("<<ComboboxSelected>>", lambda e: self.populate_filters())

        ttk.Label(filters, text="Palavra-chave", background="#ffffff").grid(row=0, column=1, sticky="w")
        q = ttk.Entry(filters, textvariable=self.query_var)
        q.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(4, 0))
        q.bind("<Return>", lambda e: self.run_search())

        ttk.Label(filters, text="Status", background="#ffffff").grid(row=0, column=2, sticky="w")
        self.status_combo = ttk.Combobox(filters, textvariable=self.status_var, state="readonly", width=14)
        self.status_combo.grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Label(filters, text="Cidade", background="#ffffff").grid(row=0, column=3, sticky="w")
        self.city_combo = ttk.Combobox(filters, textvariable=self.city_var, state="readonly", width=18)
        self.city_combo.grid(row=1, column=3, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Label(filters, text="Categoria", background="#ffffff").grid(row=0, column=4, sticky="w")
        self.cat_combo = ttk.Combobox(filters, textvariable=self.category_var, state="readonly", width=18)
        self.cat_combo.grid(row=1, column=4, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Label(filters, text="De", background="#ffffff").grid(row=0, column=5, sticky="w")
        ttk.Entry(filters, textvariable=self.date_from_var, width=12).grid(row=1, column=5, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Label(filters, text="Até", background="#ffffff").grid(row=0, column=6, sticky="w")
        ttk.Entry(filters, textvariable=self.date_to_var, width=12).grid(row=1, column=6, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Button(filters, text="Buscar", style="Primary.TButton", command=self.run_search).grid(row=1, column=7, sticky="ew", pady=(4, 0))
        for i in range(8):
            filters.columnconfigure(i, weight=1 if i in (0, 1, 3, 4) else 0)

        body = ttk.PanedWindow(root, orient="horizontal")
        body.pack(fill="both", expand=True)

        results_frame = ttk.Frame(body, padding=12, style="Card.TFrame")
        detail_frame = ttk.Frame(body, padding=12, style="Card.TFrame")
        body.add(results_frame, weight=5)
        body.add(detail_frame, weight=7)

        rtop = ttk.Frame(results_frame, style="Card.TFrame")
        rtop.pack(fill="x", pady=(0, 8))
        ttk.Label(rtop, text="Resultados", style="CardTitle.TLabel").pack(side="left")
        self.count_label = ttk.Label(rtop, text="0 encontrados", style="Text.TLabel")
        self.count_label.pack(side="right")

        cols = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(results_frame, columns=cols, show="headings", selectmode="browse")
        for key, label in COLUMNS:
            self.tree.heading(key, text=label)
            width = 70 if key == "id" else 120
            if key == "manchete":
                width = 280
            self.tree.column(key, width=width, anchor="w")
        yscroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        dtop = ttk.Frame(detail_frame, style="Card.TFrame")
        dtop.pack(fill="x", pady=(0, 8))
        ttk.Label(dtop, text="Matéria selecionada", style="CardTitle.TLabel").pack(side="left")
        ttk.Button(dtop, text="Imprimir matéria selecionada", command=self.print_selected).pack(side="right", padx=(8, 0))
        ttk.Button(dtop, text="Copiar texto", command=self.copy_text).pack(side="right")

        self.detail_title = ttk.Label(detail_frame, text="Clique em um resultado para abrir", style="CardTitle.TLabel", wraplength=680)
        self.detail_title.pack(anchor="w", pady=(0, 10))

                self.meta_text = tk.Text(detail_frame, height=6, wrap="word", font=("Arial", 10), bg="#f8fafc", fg="#111827", insertbackground="#111827", selectbackground="#c7d2fe", selectforeground="#111827", relief="flat", padx=10, pady=8)
        self.meta_text.pack(fill="x", pady=(0, 10))
        self.meta_text.configure(state="disabled")

        self.content_text = tk.Text(detail_frame, wrap="word", font=("Arial", 11), bg="#ffffff", fg="#111827", insertbackground="#111827", selectbackground="#c7d2fe", selectforeground="#111827", relief="solid", borderwidth=1, padx=12, pady=12)
        self.content_text.pack(fill="both", expand=True)
        self.content_text.configure(state="disabled")

    def selected_db_names(self):
        dbs = list_databases()
        if self.db_var.get() == "Todos os bancos":
            return dbs
        return [self.db_var.get()] if self.db_var.get() in dbs else []

    def refresh_databases(self):
        dbs = list_databases()
        values = ["Todos os bancos"] + dbs
        self.db_combo["values"] = values
        if self.db_var.get() not in values:
            self.db_var.set(values[0] if values else "Todos os bancos")

    def add_database(self):
        path = filedialog.askopenfilename(
            title="Selecione um banco SQLite",
            filetypes=[("SQLite", "*.sqlite *.db"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        dest_name = unique_dest_name(path)
        dest_path = os.path.join(DB_DIR, dest_name)
        try:
            shutil.copy2(path, dest_path)
            self.refresh_databases()
            self.db_var.set(dest_name)
            self.populate_filters()
            messagebox.showinfo("Banco adicionado", f"Banco adicionado sem substituir os existentes:\n{dest_name}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível adicionar o banco.\n\n{e}")

    def populate_filters(self):
        statuses = set()
        cities = set()
        cats = set()
        for dbname in self.selected_db_names():
            try:
                conn = get_conn(dbname)
                cur = conn.cursor()
                for col, store in [("status", statuses), ("cidade", cities), ("categoria", cats)]:
                    try:
                        cur.execute(f"SELECT DISTINCT {col} FROM materias WHERE {col} IS NOT NULL AND TRIM({col}) != '' ORDER BY {col} LIMIT 500")
                        store.update(str(r[0]) for r in cur.fetchall() if r[0])
                    except Exception:
                        pass
                conn.close()
            except Exception:
                continue
        self.status_combo["values"] = ["Todos"] + sorted(statuses)
        self.city_combo["values"] = ["Todas"] + sorted(cities)
        self.cat_combo["values"] = ["Todas"] + sorted(cats)
        if self.status_var.get() not in self.status_combo["values"]:
            self.status_var.set("Todos")
        if self.city_var.get() not in self.city_combo["values"]:
            self.city_var.set("Todas")
        if self.category_var.get() not in self.cat_combo["values"]:
            self.category_var.set("Todas")

    def build_query(self):
        keyword = self.query_var.get().strip()
        where = []
        params = []
        if keyword:
            like = f"%{keyword}%"
            where.append("(manchete LIKE ? OR resumo LIKE ? OR conteudo_texto LIKE ? OR paragrafo LIKE ?)")
            params.extend([like, like, like, like])
        if self.status_var.get() != "Todos":
            where.append("status = ?")
            params.append(self.status_var.get())
        if self.city_var.get() != "Todas":
            where.append("cidade = ?")
            params.append(self.city_var.get())
        if self.category_var.get() != "Todas":
            where.append("categoria = ?")
            params.append(self.category_var.get())
        if self.date_from_var.get().strip():
            where.append("data_da_publicacao >= ?")
            params.append(self.date_from_var.get().strip())
        if self.date_to_var.get().strip():
            where.append("data_da_publicacao <= ?")
            params.append(self.date_to_var.get().strip())
        sql = "SELECT " + ", ".join(ALL_FIELDS) + " FROM materias"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(data_da_publicacao, publish_date, updated_date) DESC LIMIT 1000"
        return sql, params

    def run_search(self):
        self.results = []
        self.selected_record = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        sql, params = self.build_query()
        for dbname in self.selected_db_names():
            try:
                conn = get_conn(dbname)
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
                conn.close()
                for row in rows:
                    rec = {field: safe_get(row, field) for field in ALL_FIELDS}
                    rec["__database"] = dbname
                    self.results.append(rec)
            except Exception as e:
                messagebox.showwarning("Aviso", f"Erro ao consultar {dbname}:\n{e}")
        self.results.sort(key=lambda r: r.get("data_da_publicacao") or r.get("publish_date") or "", reverse=True)
        self.results = self.results[:1000]
        for idx, rec in enumerate(self.results):
            values = [rec.get(k, "") for k, _ in COLUMNS]
            self.tree.insert("", "end", iid=str(idx), values=values)
        self.count_label.configure(text=f"{len(self.results)} encontrados")
        self.show_empty_detail()

    def show_empty_detail(self):
        self.detail_title.configure(text="Clique em um resultado para abrir")
        self._set_text(self.meta_text, "")
        self._set_text(self.content_text, "")

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text or "")
        widget.configure(state="disabled")

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self.results):
            return
        self.selected_record = self.results[idx]
        r = self.selected_record
        self.detail_title.configure(text=r.get("manchete") or "Sem manchete")
        meta_lines = [
            f"Banco: {r.get('__database', '')}",
            f"ID: {r.get('id', '')}",
            f"Status: {r.get('status', '')}",
            f"Data da publicação: {r.get('data_da_publicacao', '')}",
            f"Atualização: {r.get('updated_date', '')}",
            f"Cidade: {r.get('cidade', '')}",
            f"Categoria: {r.get('categoria', '')}",
            f"Imagem principal: {r.get('imagem_principal', '')}",
            f"Crédito da imagem: {r.get('credito_imagem', '')}",
        ]
        self._set_text(self.meta_text, "\n".join(meta_lines))
        content = "Resumo:\n" + (r.get("resumo") or "") + "\n\nConteúdo:\n" + (r.get("conteudo_texto") or r.get("paragrafo") or "")
        self._set_text(self.content_text, content)

    def copy_text(self):
        if not self.selected_record:
            messagebox.showinfo("Selecione uma matéria", "Clique em uma matéria antes de copiar.")
            return
        r = self.selected_record
        text = f"{r.get('manchete','')}\n\n{r.get('resumo','')}\n\n{r.get('conteudo_texto') or r.get('paragrafo') or ''}"
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", "Texto da matéria copiado.")

    def print_selected(self):
        if not self.selected_record:
            messagebox.showinfo("Selecione uma matéria", "Clique em uma matéria antes de imprimir.")
            return
        r = self.selected_record
        fields_html = "".join(
            f"<div class='box'><div class='label'>{escape(label)}</div><div class='value'>{escape(str(r.get(key, '')))}</div></div>"
            for key, label in [
                ("__database", "Banco"), ("id", "ID"), ("status", "Status"),
                ("data_da_publicacao", "Data da publicação"), ("updated_date", "Atualização"),
                ("cidade", "Cidade"), ("categoria", "Categoria"), ("imagem_principal", "Imagem principal"),
                ("credito_imagem", "Crédito da imagem"), ("publish_date", "Publish date"),
                ("unpublish_date", "Unpublish date"), ("destaque_home", "Destaque home"),
                ("carrossel", "Carrossel"), ("posicao", "Posição"), ("mundo_pet_tv", "Mundo Pet TV")
            ]
        )
        content = r.get("conteudo_texto") or r.get("paragrafo") or ""
        html = f"""
<!doctype html>
<html><head><meta charset='utf-8'><title>{escape(r.get('manchete','Matéria'))}</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 32px; color: #111827; line-height: 1.55; }}
h1 {{ font-size: 28px; line-height: 1.2; margin-bottom: 16px; }}
.meta {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 24px 0; }}
.box {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 10px; break-inside: avoid; }}
.label {{ font-size: 12px; color: #6b7280; margin-bottom: 4px; }}
.value {{ font-weight: 600; overflow-wrap: anywhere; }}
h2 {{ font-size: 16px; margin-top: 28px; }}
.content {{ white-space: pre-wrap; }}
@media print {{ body {{ padding: 18px; }} .meta {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
</style></head><body>
<h1>{escape(r.get('manchete',''))}</h1>
<div class='meta'>{fields_html}</div>
<h2>Resumo</h2><div class='content'>{escape(r.get('resumo',''))}</div>
<h2>Conteúdo completo</h2><div class='content'>{escape(content)}</div>
<script>window.onload = () => window.print();</script>
</body></html>
"""
        fd, path = tempfile.mkstemp(prefix="mundon_materia_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + path)

    def export_csv(self):
        if not self.results:
            messagebox.showinfo("Sem resultados", "Faça uma busca antes de exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Salvar resultados",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="resultados_mundon.csv"
        )
        if not path:
            return
        fields = ["__database"] + ALL_FIELDS
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for r in self.results:
                    writer.writerow({k: r.get(k, "") for k in fields})
            messagebox.showinfo("Exportado", f"Arquivo exportado:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível exportar.\n\n{e}")

    def clear_filters(self):
        self.query_var.set("")
        self.status_var.set("Todos")
        self.city_var.set("Todas")
        self.category_var.set("Todas")
        self.date_from_var.set("")
        self.date_to_var.set("")


if __name__ == "__main__":
    app = MundoNApp()
    app.mainloop()
