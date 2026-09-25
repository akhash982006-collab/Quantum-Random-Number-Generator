import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
const root='D:/PRO/kalasalingam';
const build=path.join(root,'presentation-build');
const skill='C:/Users/Akhash/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const python='C:/Users/Akhash/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/Akhash/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const c={ink:'#354653',muted:'#6C7D88',blue:'#2878BC',teal:'#248579',lav:'#7565A9'};
function t(s,txt,x,y,w,h,size=27,col=c.ink,bold=false){const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});sh.text=txt;sh.text.style={typeface:'Arial',fontSize:size,color:col,bold,autoFit:'none'};return sh;}
function s(k,title,n){let a=p.slides.add();a.background.fill=n%2?'#FFFFFF':'#F4F9FC';t(a,k.toUpperCase(),70,38,1100,30,18,c.blue,true);t(a,title,70,93,1140,78,43,c.ink,true);t(a,'Q-SENTINEL',70,671,1000,26,16,c.muted);t(a,'0'+n,1160,671,50,26,16,c.muted);return a;}
function note(a,txt){a.speakerNotes.textFrame.setText(txt);}
{
let a=s('Problem statement','The problem with QRNGs',1);
t(a,'A Quantum Random Number Generator produces bits\nused in applications such as cryptography.',72,191,1110,86,29);
t(a,'101101001011010010101101…',72,295,1120,60,40,c.blue);
t(a,'Quality can change',72,397,480,44,29,c.teal,true);
t(a,'Small bias or growing correlation\ncan make the stream more predictable.',72,457,530,100,27);
t(a,'Engineers need the full story',685,397,525,44,29,c.teal,true);
t(a,'When did it start? What changed?\nHow serious is it? What comes next?',685,457,525,100,27);
t(a,'Our goal: detect and explain changes as early as the evidence supports.',72,597,1140,50,27,c.blue,true);
note(a,'About 45 seconds. A bit is a zero or one. Quantum processes can provide randomness, but the measurement and processing pipeline can introduce bias or dependence. A pass/fail summary is useful, but it does not alone tell an engineer when the behavior changed. Avoid claiming every existing validator only provides pass/fail. Bias means unequal zero/one frequency. Correlation means a relationship between bits.\nSource: user-supplied WO-012 brief and presentation outline.');
}
{
let a=s('Proposed solution','Q-Sentinel: continuous reliability monitoring',2);
t(a,'The stream becomes a timeline of evidence.',72,191,1120,48,30,c.blue,true);
const rows=[['01','Receive & check','Validate input and divide it into windows.'],['02','Measure & compare','Track entropy, bias and patterns against a reference.'],['03','Detect & explain','Flag persistent changes and identify statistical signatures.'],['04','Recommend & record','Suggest investigation steps and save a health passport.']];
rows.forEach((r,i)=>{let y=268+i*78;t(a,r[0],72,y,65,48,31,c.blue,true);t(a,r[1],164,y,385,48,29,c.ink,true);t(a,r[2],555,y,650,65,25);});
t(a,'Healthy     →     Early Warning     →     Degraded     →     Critical',72,604,1130,42,28,c.teal,true);
note(a,'About 45 seconds. Each window contains a fixed number of bits. We preserve the order so we can locate the change. The display also has Calibrating and Insufficient Data states. A reference can come from a supplied dataset. Otherwise the first 30 complete windows form an explicitly unverified baseline. The platform does not know that this initial data is physically healthy.\nSource: q-sentinel/README.md and user outline.');
}
{
let a=s('Technical approach','Small windows reveal how behavior changes',3);
t(a,'1,000,000 bits  →  100 windows of 10,000 bits',72,189,1140,50,33,c.blue,true);
t(a,'Measure',72,282,330,42,29,c.teal,true);
t(a,'Entropy: uncertainty\nMin entropy: dominant bit\nBias: zero/one balance\nCorrelation: dependence',72,342,345,174,25);
t(a,'Test',460,282,345,42,29,c.teal,true);
t(a,'Six NIST test families\nFrequency / Block Frequency\nRuns / Longest Run\nDFT / Cumulative Sums',460,342,365,174,25);
t(a,'Detect',883,282,330,42,29,c.teal,true);
t(a,'CUSUM accumulates\nchanges from the baseline.\nPersistent evidence\ntriggers an alert.',883,342,330,174,25);
t(a,'Working prototype: Python, Streamlit, NumPy, Pandas, SciPy, Plotly and SQLite.',72,554,1135,40,23,c.blue,true);
t(a,'Q-Advisor uses explainable rules. No trained AI model or paid API is required.',72,602,1135,39,23,c.muted);
note(a,'About 60 seconds. Shannon, min and collision entropy here are empirical marginal estimates. Min entropy reflects the most probable bit, not all sequence predictability. CUSUM stands for cumulative sum. It adds evidence of deviations from a frozen baseline and helps detect persistent changes. DFT checks spectral structure. Cumulative Sums checks excursions of the bitstream random walk. The prototype implements six NIST families, not the full suite. Approximate Entropy and Serial are future additions. Q-Advisor summarizes measured evidence with deterministic rules. Statistical tests cannot establish quantum origin.\nSources: q-sentinel/README.md; q-sentinel/nist/; NIST SP 800-22 Rev.1a https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final');
}
{
let a=s('Feasibility & viability','A prototype we can test without quantum hardware',4);
t(a,'Failure Lab',72,197,540,43,30,c.teal,true);
t(a,'Inject bias, correlation, periodicity,\nrepetition, bursts, gradual drift\nor sudden collapse.',72,257,535,124,28);
t(a,'Healthy simulation → Inject a fault\n→ Analyze the evidence → Inspect bits',72,412,535,103,27,c.blue,true);
t(a,'Classical simulation, clearly labeled.\nReal hardware validation comes next.',72,553,540,82,24,c.muted);
t(a,'Path to a laboratory pilot',690,197,520,43,30,c.teal,true);
t(a,'Current: local Streamlit application\nwith saved sessions and PDF reports.',690,257,520,94,27);
t(a,'Proposed cloud version',690,380,520,40,25,c.blue,true);
t(a,'React + Vite / FastAPI + Python\nCloudflare + Render / Firebase',690,429,520,85,25);
t(a,'Future inputs: Serial, TCP,\nWebSocket and MQTT adapters.',690,553,520,82,24,c.muted);
note(a,'About 55 seconds. No quantum hardware is needed to demonstrate the analysis workflow. The engineering simulation generates classical pseudorandom bits and injects known faults. Keep simulation ground truth separate from detector inputs. Existing evaluation detected 71 of 75 simulated fault scenarios, with 4 misses and 2 false alert events across 350 healthy monitoring windows. These results do not validate physical hardware performance. The current working app is local. React, FastAPI, Firebase, Cloudflare and Render are a proposed deployment architecture from the supplied outline, not a completed deployment. First users are QRNG researchers and device test engineers. A real-data pilot should establish value before production deployment.\nSources: q-sentinel/output/evaluation-summary.json; q-sentinel/README.md; user deployment proposal.');
}
{
let a=s('Impact & benefits','A clearer investigation for engineers',5);
const rows=[['Earlier attention','Surface persistent changes before they become severe,\nwhen the measured evidence supports it.'],['Focused troubleshooting','Locate affected windows and inspect changes\nin entropy, bias and correlation.'],['Continuous history','Track degradation and recovery across sessions.\nCompare the stream before and after an adjustment.'],['Health passport','Share metrics, test results, events and recommendations\nin a traceable record.']];
rows.forEach((r,i)=>{let y=202+i*105;t(a,r[0],72,y,410,46,29,c.teal,true);t(a,r[1],515,y,700,83,26);});
t(a,'For QRNG researchers, device engineers and laboratory teams.',72,627,1130,36,24,c.blue,true);
note(a,'About 45 seconds. These are intended engineering benefits, not measured reductions in downtime or financial savings. A useful diagnosis says the statistical signature is consistent with bias or correlation. It does not prove a detector is broken. The health score is an operational summary, not a probability of security. Monitoring results can guide inspection of raw acquisition and post-processing.\nSource: user outline and q-sentinel/README.md.');
}
{
let a=s('Innovation & demo','The warning comes with evidence',6);
t(a,'A pass/fail summary',72,194,535,44,29,c.muted,true);
t(a,'QRNG data → NIST → Result',72,250,535,48,28);
t(a,'Q-Sentinel adds the investigation',690,194,530,44,28,c.teal,true);
t(a,'Measure → Compare → Detect\n→ Explain → Recommend',690,250,525,85,28,c.blue,true);
t(a,'Live demo',72,369,450,42,29,c.teal,true);
t(a,'1   Start a healthy simulation\n2   Inject gradual degradation\n3   Inspect the first flagged window\n4   Export the health passport',72,427,560,182,28);
t(a,'What judges will see',690,369,525,42,29,c.teal,true);
t(a,'Measured entropy, bias and correlation\nAlerts linked to specific windows\nAn explanation of the evidence\nA suggested next investigation',690,427,525,182,26);
t(a,'Demo results vary with the data. Statistical evidence does not prove quantum origin.',72,629,1140,34,21,c.muted);
note(a,'About 50 seconds, then demonstrate. Start healthy, inject gradual degradation, inspect the first actual event and open Q-Advisor. Use the computed values on screen. The supplied draft numbers entropy 0.998, health 98 and Window 63 are illustrative, not fixed outcomes. Do not promise a fixed order of alerts and NIST failures. The reproducible existing demo report first enters Early Warning at window 56, Degraded at 66 and Critical at 92, with a temporary recovery between. It uses gradual bias followed by a stuck-output segment. Other faults need not increase bias and correlation together. Suggested conclusion: Q-Sentinel connects statistical validation to a repeatable engineering investigation.\nSources: user outline; q-sentinel/DEMO.md; q-sentinel/output/sample-passport.json.');
}
const candidate=path.join(build,'content-candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const final=path.join(root,'deliverables','Q-Sentinel_Six_Slide_Pitch.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:6,requiredNativeChartOwnerSlides:[],requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'content-validation.json')});
const checked=await PresentationFile.importPptx(await FileBlob.load(final));
await fs.mkdir(path.join(build,'content-previews'),{recursive:true});
for(let i=0;i<checked.slides.items.length;i++){const png=await checked.export({slide:checked.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,'content-previews',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));}
console.log(final);
