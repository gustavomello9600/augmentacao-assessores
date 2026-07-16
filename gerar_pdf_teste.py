"""Gera um PDF de relatorio XPerformance ficcional usando fpdf2."""
from fpdf import FPDF
import random
from datetime import datetime

class XPerformancePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'XPerformance - Relatorio de Performance', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, 'Confidencial - Produzido por XP Investimentos', align='C', new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} - Gerado em {datetime.now().strftime("%d/%m/%Y")}', align='C')


def gerar_pdf_cliente(nome_cliente: str, output_path: str) -> str:
    pdf = XPerformancePDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Dados do cliente ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, f'Cliente: {nome_cliente}', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, f'Data do relatorio: {datetime.now().strftime("%d/%m/%Y")}', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, 'Periodo de analise: Ultimos 12 meses', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # --- Resumo da Carteira ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  RESUMO DA CARTEIRA', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    patrimonio = round(random.uniform(150000, 800000), 2)
    rentabilidade_mes = round(random.uniform(-1.5, 4.5), 2)
    rentabilidade_ano = round(random.uniform(4.0, 18.0), 2)
    percentual_cdi = round(random.uniform(95, 145), 1)
    ganho_mes = round(patrimonio * (rentabilidade_mes / 100), 2)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(40, 40, 40)

    dados_resumo = [
        ('Patrimonio Total', f'R$ {patrimonio:,.2f}'),
        ('Rentabilidade no Mes', f'{rentabilidade_mes:+.2f}%'),
        ('Rentabilidade no Ano', f'{rentabilidade_ano:+.2f}%'),
        ('% do CDI (12 meses)', f'{percentual_cdi:.1f}%'),
        ('Ganho no Mes', f'R$ {ganho_mes:,.2f}'),
    ]

    for label, valor in dados_resumo:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(80, 7, f'  {label}:', border=0)
        pdf.set_font('Helvetica', '', 10)
        if 'Ganho' in label or 'Rentabilidade' in label:
            if rentabilidade_mes > 0:
                pdf.set_text_color(0, 128, 0)
            elif rentabilidade_mes < 0:
                pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 7, valor, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(40, 40, 40)

    pdf.ln(6)

    # --- Alocacao por Classe de Ativo ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  ALOCACAO POR CLASSE DE ATIVO', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    classes = [
        ('Renda Fixa Pos-Fixada', round(random.uniform(25, 45), 1), round(random.uniform(95, 110), 1)),
        ('Renda Fixa Inflacao', round(random.uniform(10, 25), 1), round(random.uniform(80, 105), 1)),
        ('Renda Variavel - Acoes Brasil', round(random.uniform(8, 20), 1), round(random.uniform(90, 150), 1)),
        ('Fundos Multimercados', round(random.uniform(5, 15), 1), round(random.uniform(85, 120), 1)),
        ('Fundos Imobiliarios (FIIs)', round(random.uniform(3, 10), 1), round(random.uniform(70, 110), 1)),
        ('Private Equity / Alternativos', round(random.uniform(2, 8), 1), round(random.uniform(100, 200), 1)),
    ]

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 235, 245)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(80, 7, '  Classe de Ativo', border=1, fill=True)
    pdf.cell(40, 7, '% Carteira', border=1, fill=True, align='C')
    pdf.cell(50, 7, '% CDI (12m)', border=1, fill=True, align='C')
    pdf.ln()

    for classe, pct, cdi in classes:
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(80, 6, f'  {classe}', border=1)
        pdf.cell(40, 6, f'{pct:.1f}%', border=1, align='C')
        if cdi >= 100:
            pdf.set_text_color(0, 128, 0)
        else:
            pdf.set_text_color(200, 80, 0)
        pdf.cell(50, 6, f'{cdi:.1f}%', border=1, align='C')
        pdf.set_text_color(40, 40, 40)
        pdf.ln()

    pdf.ln(6)

    # --- Evolucao Patrimonial (simulada) ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  EVOLUCAO PATRIMONIAL (12 MESES)', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(40, 40, 40)

    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    valor_base = patrimonio * 0.85
    pdf.cell(0, 5, '  (Grafico de barras - valores em R$ mil)', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for i, mes in enumerate(meses):
        valor_mes = valor_base * (1 + random.uniform(-0.02, 0.04) * (i + 1))
        barra_len = int((valor_mes / patrimonio) * 40)
        barra = '#' * barra_len
        pdf.cell(20, 5, f'  {mes}', border=0)
        pdf.cell(0, 5, f'{barra} R$ {valor_mes/1000:,.0f}k', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # --- Disclaimer ---
    pdf.set_font('Helvetica', 'I', 7)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 4,
        'Este relatorio e confidencial e destinado exclusivamente ao cliente acima identificado. '
        'Rentabilidade passada nao representa garantia de rentabilidade futura. '
        'Os investimentos mencionados estao sujeitos a riscos de mercado. '
        'Este documento foi gerado automaticamente pela plataforma XPerformance - XP Investimentos CCTVM S/A. '
        'CNPJ: 02.332.886/0001-04. Ouvidoria: 0800-722-3730.'
    )

    pdf.output(output_path)
    print(f'[+] PDF gerado: {output_path} ({patrimonio:,.0f} patrimonio, {rentabilidade_mes:+.2f}% mes)')
    return output_path


if __name__ == '__main__':
    import sys
    nome = sys.argv[1] if len(sys.argv) > 1 else 'Joao da Silva'
    path = sys.argv[2] if len(sys.argv) > 2 else '/tmp/relatorio_xperformance.pdf'
    gerar_pdf_cliente(nome, path)
