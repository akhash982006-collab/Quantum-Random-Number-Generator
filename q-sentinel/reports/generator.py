import io,json
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing,String,Line,PolyLine

def export_json(result): return json.dumps(result,indent=2,allow_nan=False).encode()

def export_csv(result):
    return pd.json_normalize(result['windows']).drop(columns=['tests','z'],errors='ignore').to_csv(index=False).encode()

def chart(rows,key,title):
    d=Drawing(470,150); d.add(String(0,135,title,fontSize=11,fillColor=colors.HexColor('#183c79')))
    values=[(i,r.get(key)) for i,r in enumerate(rows) if r.get(key) is not None]
    if len(values)<2: d.add(String(0,80,'Insufficient comparable windows',fontSize=9)); return d
    lo=min(v for _,v in values); hi=max(v for _,v in values); hi=max(hi,lo+1e-5)
    pts=[(35+i/max(1,len(rows)-1)*425,25+(v-lo)/(hi-lo)*95) for i,v in values]
    d.add(Line(35,25,460,25,strokeColor=colors.lightgrey)); d.add(PolyLine(pts,strokeColor=colors.HexColor('#426fe7'),strokeWidth=1.3))
    d.add(String(0,115,f'{hi:.3f}',fontSize=8)); d.add(String(0,25,f'{lo:.3f}',fontSize=8)); d.add(String(35,8,'Window 1',fontSize=8)); d.add(String(400,8,f"Window {len(rows)}",fontSize=8))
    return d

def pdf(result,comparison=None):
    output=io.BytesIO(); styles=getSampleStyleSheet(); styles['BodyText'].fontSize=9; styles['BodyText'].leading=13
    story=[]
    def p(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)),styles[style]))
        if not style.startswith('Heading'): story.append(Spacer(1,7))
    def heading(text): p(text,'Heading2')
    def table(headers,rows,widths):
        data=[[Paragraph(escape(str(v)),styles['BodyText']) for v in row] for row in [headers]+rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT'); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7edfa')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#8095bd'))])); story.append(t)
    p('Q-GAURD','Title'); p('QRNG Reliability & Forensic Health Passport','Heading2')
    p(f"Session {result['session_id']} | {result['timestamp']}")
    heading('Executive summary'); p(result['advisor'])
    heading('Dataset and data quality'); p(result['metadata'].get('name','Dataset')); p(f"Source: {result['metadata'].get('source','unknown')}; analyzed bits: {result['metadata']['bits']:,}; complete windows: {result['data_quality']['complete_windows']}; excluded trailing bits: {result['data_quality']['trailing_bits']}.")
    p('SHA-256: '+result['metadata']['sha256']); p('Baseline: '+result['baseline']['status'])
    heading('Entropy analysis'); table(['Metric','Whole-stream value'],[[k,f'{result["overall"][k]:.6f}'] for k in ['shannon','min_entropy','collision','block_entropy','bias','autocorrelation'] if result['overall'][k] is not None],[220,250])
    p('Shannon, min and collision entropy are empirical marginal estimates. Dependence and block metrics must also be inspected.')
    story.append(PageBreak()); heading('Temporal evidence'); story.append(chart(result['windows'],'shannon','Marginal Shannon entropy')); story.append(chart(result['windows'],'health','Operational health / 100'))
    heading('NIST statistical screening'); table(['Test','P-value','Result'],[[r['name'],'N/A' if r['p_value'] is None else f"{r['p_value']:.6g}",r['status']] for r in result['nist']],[230,100,140])
    p('Six test families; Cumulative Sums has two directions. Alpha = 0.01. Inapplicable families are excluded from pass rates. A pass does not establish quantum origin.')
    for r in result['nist']:
        if r['p_value'] is None: p(r['name']+': '+r['interpretation'])
    story.append(PageBreak()); heading('Entropy fingerprint and diagnosis')
    last=result['windows'][-1] if result['windows'] else {}
    table(['Component','Stability / 100'],[[k,'Unavailable' if v is None else f'{v:.2f}'] for k,v in last.get('components',{}).items()],[270,200])
    p('Relative weights: '+', '.join(f'{k} {v}' for k,v in result['config']['weights'].items())+' (renormalized over available components)')
    p('Strongest signature matches: '+', '.join(f'{k} {v:.1f}/100' for k,v in sorted(last.get('signatures',{}).items(),key=lambda item:item[1],reverse=True)[:4]))
    heading('Degradation events and change points')
    selected=sorted([e for e in result['events'] if e['kind']!='Change point'][:12]+[e for e in result['events'] if e['kind']=='Change point'][:8],key=lambda e:e['window'])
    table(['Window','Event','State'],[[e['window'],e['kind'],e['state']] for e in selected] or [['-','No detected events','-']],[70,220,180])
    if len(result['events'])>len(selected): p('State transitions and first eight change events shown, up to 20 records. Full event log is included in JSON export.')
    
    incons = result.get('inconsistencies', [])
    inc_sum = result.get('inconsistency_summary', {})
    if incons:
        heading('Inconsistency Explorer Dossier')
        table(['Metric', 'Summary Value'], [
            ['Total Inconsistency Events', str(inc_sum.get('total_events', len(incons)))],
            ['Unique Affected Windows', str(inc_sum.get('unique_affected_windows', 0))],
            ['Total Flagged Bit Ranges', str(inc_sum.get('flagged_ranges_count', 0))],
            ['First Detected Event', str(inc_sum.get('first_detected', 'None'))],
            ['Primary Signature Type', str(inc_sum.get('most_common_type', 'None'))],
            ['Highest Severity Level', str(inc_sum.get('highest_severity', 'Healthy'))]
        ], [200, 270])
        p('Normalized Inconsistency Records:')
        inc_rows = []
        for inc in incons[:10]:
            w_span = f"W{inc['first_detected_window']}" if inc['affected_windows_count'] == 1 else f"W{inc['affected_windows'][0]}–W{inc['affected_windows'][-1]} ({inc['affected_windows_count']}w)"
            inc_rows.append([inc['id'], inc['type'], inc['severity'], w_span, f"{inc['bit_start']:,}–{inc['bit_end']:,}"])
        table(['ID', 'Type', 'Severity', 'Windows', 'Bit Range'], inc_rows, [60, 110, 80, 100, 120])
        p('Measurement basis: Statistical metrics represent window-level inspection evidence; physical onset is unknown without external hardware telemetry.')
    story.append(PageBreak())
    heading('Risk assessment'); p(result['forecast']['reason'])
    if result['forecast']['available']: p(f"Conditional threshold crossing: {result['forecast']['windows_to_threshold']:.1f} windows. Trend slope: {result['forecast']['slope']:.4f} health points/window.")
    heading('Recommendations'); p(result['advisor'])
    heading('Historical comparison')
    if comparison: p(f"Reference session {comparison['session_id']}: marginal Shannon {comparison['overall']['shannon']:.6f}; current {result['overall']['shannon']:.6f}.")
    else: p('No historical comparison selected; no historical improvement or deterioration is inferred.')
    heading('Methodology'); p('NIST SP 800-22 Rev.1a sections 2.1-2.4, 2.6 and 2.13. Two-sided CUSUM on standardized bias, lag-one dependence, spectral concentration and 8-bit block entropy. Allowance 0.5; frozen baseline; two-window escalation persistence and five-window recovery evidence. Score components and calibration details are included in the JSON report.')
    cal=result['calibration']
    if cal: p(f"Calibration threshold {cal['threshold']:.3f}; {cal['training_windows']} training and {cal['validation_windows']} validation windows. Observed held-out CUSUM events: {cal['false_alerts']}. This limited synthetic sample does not establish a zero false-alert probability. Seeds: {cal['calibration_seeds']}.")
    p('Software: '+result['version'])
    p('Sources: https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final and https://csrc.nist.gov/pubs/sp/800/90/b/final')
    heading('Scientific Interpretation'); p(result['limitations'])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#65738d')); canvas.drawString(42,25,'Q-GAURD | Statistical evidence, not quantum certification'); canvas.drawRightString(552,25,str(doc.page))
    SimpleDocTemplate(output,pagesize=(595,842),rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
