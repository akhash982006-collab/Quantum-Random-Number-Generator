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
const slides=JSON.parse(await fs.readFile(path.join(build,'team-pitch-content.json'),'utf8'));
for(let i=0;i<slides.length;i++){
 const d=slides[i]; const a=s(d.section,d.title,i+1);
 if(d.background) a.background.fill=d.background;
 for(const [txt,x,y,w,h,size,col,bold] of d.items) t(a,txt,x,y,w,h,size,c[col],bold);
 note(a,d.notes);
}
const candidate=path.join(build,'team-candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const final=path.join(root,'deliverables','Q-Sentinel_Gladiators_Final.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:6,requiredNativeChartOwnerSlides:[],requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'gladiators-validation.json')});
const checked=await PresentationFile.importPptx(await FileBlob.load(final));
await fs.mkdir(path.join(build,'team-previews'),{recursive:true});
for(let i=0;i<checked.slides.items.length;i++){const png=await checked.export({slide:checked.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,'team-previews',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));}
console.log(final);



