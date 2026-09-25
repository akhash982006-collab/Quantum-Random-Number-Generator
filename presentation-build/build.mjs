import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const root='D:/PRO/kalasalingam';
const build=path.join(root,'presentation-build');
const skill='C:/Users/Akhash/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const python='C:/Users/Akhash/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const report=JSON.parse(await fs.readFile(path.join(root,'q-sentinel/output/sample-passport.json'),'utf8'));
const evaluation=JSON.parse(await fs.readFile(path.join(root,'q-sentinel/output/evaluation-summary.json'),'utf8'));
const pres=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#34424F',muted:'#687B88',blue:'#2878BC',teal:'#268C83',light:'#F3F9FD',white:'#FFFFFF'};
function text(s,content,x,y,w,h,size=26,color=C.ink,bold=false){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=content;
  sh.text.style={typeface:'Arial',fontSize:size,color,bold,autoFit:'none'};
  return sh;
}
function slide(title,num){
  const s=pres.slides.add(); s.background.fill=C.white;
  text(s,title,70,48,1120,76,44,C.ink,true);
  text(s,'Q-SENTINEL',70,667,1050,28,17,C.muted);
  text(s,String(num).padStart(2,'0'),1160,667,55,28,17,C.muted);
  return s;
}
function note(s,body,source=''){s.speakerNotes.textFrame.setText(body+(source?'\n\nSources: '+source:''));}

// 1. Minimal, editable typographic cover.
{
 const s=pres.slides.add(); s.background.fill=C.light;
 text(s,'Q-SENTINEL',78,110,1110,104,76,C.blue,true);
 text(s,'QRNG reliability and early warning',82,230,1070,72,43,C.ink,true);
 text(s,'Helping engineers find when a random bitstream changes\nand understand the evidence behind it.',84,337,1070,112,30);
 text(s,'Quantum Random Number Generator (QRNG) Entropy Validator',84,550,1100,52,23,C.muted);
 text(s,'Hackathon prototype',84,609,1000,36,20,C.teal);
 note(s,'Opening, about 30 seconds: A QRNG uses a quantum physical process to generate random numbers. The detector and software around it can still introduce unwanted patterns. Q-Sentinel analyzes the resulting binary data and helps engineers investigate changes. Our current prototype works with uploaded files and classical simulated streams.');
}
// 2. Problem statement and user need.
{
 const s=slide('Problem statement',2);
 text(s,'Reliable randomness needs ongoing checks',72,146,1100,56,33,C.blue,true);
 text(s,'The challenge: ingest quantum optical RNG data, run NIST statistical\ntests, and map entropy degradation over time.',74,226,1100,100,29);
 text(s,'What can go wrong?',74,369,500,45,27,C.teal,true);
 text(s,'Too many zeros or ones\nRepeated patterns\nSudden or gradual changes',74,428,510,145,27);
 text(s,'What engineers need to know',665,369,540,45,27,C.teal,true);
 text(s,'When did the change begin?\nWhich measurements changed?\nWhat should we investigate?',665,428,540,145,27);
 text(s,'Entropy describes uncertainty. A high single-bit entropy value can still hide repetition.',74,611,1110,36,21,C.muted);
 note(s,'About 45 seconds: Define a bitstream as a sequence of zeros and ones. NIST tests look for specific statistical abnormalities. A whole-file result does not by itself explain when an issue began. A balanced repeating 0101 sequence illustrates why zero/one balance alone is insufficient. Q-Sentinel accepts already-digitized bits, not analog optical waveforms.','User-supplied competition brief, WO-012. NIST SP 800-22 Rev.1a: https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final');
}
// 3. Proposed solution with editable chart drawn from the real demo report.
{
 const s=slide('Proposed solution',3);
 text(s,'A continuous record of changes and their evidence',72,140,1120,56,31,C.blue,true);
 const sample=report.windows.filter(w=>w.window>=31 && (w.window-31)%5===0);
 const chart=s.charts.add('line',{
   position:{left:65,top:222,width:775,height:345},
   categories:sample.map(w=>String(w.window)),
   series:[{name:'Operational health',values:sample.map(w=>w.health),line:{fill:C.blue,width:3},marker:{symbol:'circle',size:5}}],
   hasLegend:false,lineOptions:{smooth:false},
   xAxis:{title:'Window number',textStyle:{fontSize:17,fill:C.muted},majorGridlines:null},
   yAxis:{title:'Health score / 100',min:0,max:100,majorUnit:25,textStyle:{fontSize:17,fill:C.muted},majorGridlines:{fill:'#E5ECF0',width:1}},
   chartFill:C.white,plotAreaFill:C.white,chartLine:{fill:'none',width:0}
 });
 applyPresentationChartFont(chart,{fontFamily:'Arial'});
 text(s,'56',896,225,260,58,43,C.teal,true);
 text(s,'First Early Warning',896,282,300,46,24);
 text(s,'66',896,352,260,58,43,C.blue,true);
 text(s,'Degraded state',896,409,300,42,24);
 text(s,'92',896,473,260,58,43,C.blue,true);
 text(s,'Critical state',896,530,300,42,24);
 text(s,'Engineers can open a flagged window, inspect the bits, and save an evidence-based report.',74,595,1120,44,24);
 text(s,'Simulated demonstration. Every fifth monitoring window shown. Scores are computed from the bits.',74,638,1115,28,17,C.muted);
 note(s,'About 50 seconds: The fixed scenario starts a slow bias drift at window 41 and introduces stuck output at window 91. The detector sees the resulting bits, not the injection labels. It flags Early Warning at window 56, temporarily returns to Healthy at 64, becomes Degraded at 66 and Critical at 92. The graph is sampled every fifth window for readability. The event labels come from the full-resolution results. Show that the early warning is an observation from this demo, not a guaranteed sequence for every fault. Health is an operational indicator, not a security probability.','q-sentinel/output/sample-passport.json, windows and events. q-sentinel/simulation/qrng_twin.py, guided_demo().');
}
// 4. Technical approach explained without equations or a crowded architecture diagram.
{
 const s=slide('Technical approach',4);
 const rows=[
  ['01','Receive and check','Read TXT, CSV or binary files, or a simulated stream.'],
  ['02','Analyze small windows','Measure entropy, bias and patterns in each 10,000-bit window.'],
  ['03','Detect persistent change','Compare with a baseline. CUSUM accumulates small deviations.'],
  ['04','Explain and preserve','Show the affected bits, recommendations and a saved health passport.']
 ];
 rows.forEach((r,i)=>{const y=157+i*102;text(s,r[0],74,y,70,45,30,C.blue,true);text(s,r[1],173,y,1030,40,27,C.ink,true);text(s,r[2],173,y+44,1030,42,24,C.muted);});
 text(s,'Python + Streamlit     NumPy / Pandas / SciPy     Plotly     SQLite + ReportLab',74,583,1120,42,23,C.teal,true);
 text(s,'Six NIST test families. Transparent statistical rules. Q-Advisor summarizes measured evidence.',74,629,1130,31,21,C.muted);
 note(s,'About 60 seconds: Windowing means dividing a long stream into equal sections so we can locate changes. A baseline is reference behavior, taken from a supplied dataset or the first 30 windows, which we label unverified. CUSUM stands for cumulative sum control chart and adds up repeated small deviations. Six NIST families are Frequency, Block Frequency, Runs, Longest Run, DFT, and Cumulative Sums in both directions. Forecasting uses a robust Theil-Sen slope over 20 comparable windows with a Spearman trend check. Q-Advisor uses deterministic rules and templates, not a generative AI model. A worker handles analysis while the interface polls progress.','q-sentinel/core/, q-sentinel/nist/suite.py, q-sentinel/requirements.txt. NIST SP 800-22: https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final');
}
// 5. Honest evidence plus a plausible pilot route, not unsupported market claims.
{
 const s=slide('Feasibility & viability',5);
 text(s,'Working prototype',74,159,355,46,28,C.teal,true);
 text(s,'71 / 75',74,228,350,76,54,C.blue,true);
 text(s,'simulated fault scenarios\ndetected',74,317,355,88,27);
 text(s,'4 missed scenarios\n2 false alerts across\n350 healthy windows',74,432,355,137,24);
 text(s,'Local performance',467,159,355,46,28,C.teal,true);
 text(s,'0.9 sec',467,228,350,76,54,C.blue,true);
 text(s,'to analyze one million bits\non the test machine',467,317,355,88,27);
 text(s,'10 million bits: 10.3 sec\nNo paid API required\nFiles stay on the laptop',467,432,355,137,24);
 text(s,'Practical pilot',870,159,350,46,28,C.teal,true);
 text(s,'QRNG labs',870,236,350,65,39,C.blue,true);
 text(s,'First users: researchers\nand device test engineers',870,317,350,88,27);
 text(s,'Pilot with real recordings\nTune alert thresholds\nAdd a hardware adapter',870,432,350,137,24);
 text(s,'Early-warning comparison: 16 earlier, 41 simultaneous, 3 later, 15 without a joint detection time.',74,600,1140,38,20,C.muted);
 text(s,'Synthetic evaluation only. These results do not establish performance on physical QRNG hardware.',74,636,1125,29,18,C.muted);
 note(s,'About 60 seconds: These are measured prototype results, not claims of production readiness. Across five evaluation seeds, 71 of 75 injected-fault scenarios were detected. Do not call this overall accuracy because it does not incorporate the false-alert rate. The NIST-only comparator requires two applicable families failing in two consecutive windows. Of the 75 fault cases, 16 had earlier alerts, 41 equal detection times, 3 later alerts and 15 no jointly available detection time. Those 15 are not early-warning wins. The 2 false alert transitions occurred across 350 healthy monitoring windows. Runtime is approximately 0.866 seconds for one million bits and 10.344 seconds for ten million bits in the available Windows environment. Commercial demand and pricing have not been validated. The next viable step is a laboratory pilot, not a security-critical deployment.','q-sentinel/output/evaluation-summary.json; q-sentinel/output/evaluation.csv; q-sentinel/VALIDATION.md.');
}
// 6. Benefits stated as intended outcomes, with a clear boundary and next step.
{
 const s=slide('Impact & benefits',6);
 text(s,'A clearer investigation for QRNG engineers',74,147,1100,55,32,C.blue,true);
 text(s,'Earlier attention',74,254,390,45,28,C.teal,true);
 text(s,'Surface small, persistent changes\nthat deserve investigation.',514,253,675,82,28);
 text(s,'More focused debugging',74,370,410,45,28,C.teal,true);
 text(s,'Locate affected windows and inspect\nthe measurements behind each alert.',514,369,675,82,28);
 text(s,'Repeatable comparisons',74,486,410,45,28,C.teal,true);
 text(s,'Compare runs after adjustments and\nshare a traceable health passport.',514,485,675,82,28);
 text(s,'Next step: validate with real QRNG data and hardware measurements.',74,594,1100,39,25,C.blue,true);
 text(s,'Statistical evidence alone cannot establish quantum origin or cryptographic security.',74,636,1110,29,20,C.muted);
 note(s,'Closing, about 40 seconds: Present these as intended engineering benefits, not measured reductions in downtime or cost. Our current product is most suitable for research and device development. The contribution is the connected workflow: statistical monitoring leads to exact-window evidence and a reproducible investigation record. A hardware diagnosis still requires device measurements. The simulator is classical. Formal SP 800-90B assessment and the remaining NIST test families are future work. Finish by offering to show the Failure Lab and forensic view.','q-sentinel/README.md; q-sentinel/core/engine.py. NIST SP 800-90B: https://csrc.nist.gov/pubs/sp/800/90/b/final');
}

await fs.mkdir(path.join(build,'previews'),{recursive:true});
for (let i=0;i<pres.slides.items.length;i++){
 const slide=pres.slides.items[i];
 const png=await pres.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(build,'previews',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
const final=path.join(root,'deliverables','Q-Sentinel_Judges_6_Slides.pptx');
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:6,requiredNativeChartOwnerSlides:[3],requiredNativeTableOwnerSlides:[],
 materializeLiteralChartWorkbooks:true,nativeChartTargetApplication:'powerpoint',
 fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')
});
console.log(JSON.stringify(result));
