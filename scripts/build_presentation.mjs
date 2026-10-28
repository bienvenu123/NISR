import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const runtimeModules = process.env.RUNTIME_NODE_MODULES ?? 'C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtimeModules,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const skillDir = 'C:/Users/HP/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/presentations';
const finalizer = await import(`file:///${skillDir.replaceAll('\\','/')}/container_tools/artifact_tool_utils.mjs`);
const W = 1280, H = 720;
const C = { ink:'#172B3A', navy:'#17365D', teal:'#087E8B', aqua:'#DCEFF0', pale:'#F3F6F8', gray:'#52616B', muted:'#788690', orange:'#E08A32', red:'#C35A4B', white:'#FFFFFF', line:'#D9E1E6' };
const pres = Presentation.create({ slideSize:{width:W,height:H} });
const noLine = {style:'solid',fill:'none',width:0};
function rect(s,x,y,w,h,fill,r=0,line='none') {
  const sh=s.shapes.add({geometry:r?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:line==='none'?noLine:{style:'solid',fill:line,width:1}}); return sh;
}
function text(s,txt,x,y,w,h,size=22,color=C.ink,bold=false,opts={}) {
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:noLine});
  sh.text=txt; sh.text.style={fontFamily:'Aptos',fontSize:size,color,bold,verticalAlignment:'middle',wrap:true,...opts}; return sh;
}
function base(title,sub,n){
  const s=pres.slides.add(); s.background.fill=C.white;
  rect(s,0,0,14,H,C.teal); text(s,title,64,34,1145,54,32,C.ink,true); 
  if(sub) text(s,sub,66,92,1120,32,15,C.gray,false);
  rect(s,64,666,1150,1,C.line); text(s,'EICV7 • Rwanda • descriptive district analysis',66,675,850,22,11,C.muted,false); text(s,String(n).padStart(2,'0'),1165,675,48,22,11,C.muted,true);
  return s;
}
function note(s,source){s.speakerNotes.text=source;}
function pill(s,label,x,y,w,fill=C.aqua,color=C.teal){rect(s,x,y,w,30,fill,1);text(s,label,x+10,y+1,w-20,27,12,color,true);}

// 1 — Cover
{
 const s=pres.slides.add(); s.background.fill=C.navy; rect(s,0,0,16,H,C.teal);
 text(s,'RWANDA  |  EICV7 2023–24',76,70,550,30,15,'#A9DADC',true,{characterSpacing:1});
 text(s,'Double exclusion\nin Rwanda',76,158,870,170,54,C.white,true);
 text(s,'Where poor households are missed by VUP and bank or mobile accounts',80,356,760,66,25,'#D9E4EA');
 rect(s,80,472,590,2,C.teal); text(s,'District evidence to guide local service reviews',80,496,700,42,20,C.white);
 text(s,'Weighted analysis of EICV7 household microdata',80,630,760,28,14,'#B8C8D2');
 note(s,'Sources: NISR EICV7 microdata catalog and EICV7 Main Indicators Report. Fieldwork: October 2023–October 2024. Analysis is descriptive.');
}
// 2 — Problem and definition
{
 const s=base('Two service gaps can overlap in the same poor household','A district level signal for investigation—not a test of VUP eligibility.',2);
 const cards=[
  {x:68,k:'SOCIAL PROTECTION',t:'No observed VUP participation',b:'No positive participation flag across five EICV7 VUP modules.',color:C.teal},
  {x:450,k:'FINANCIAL ACCESS',t:'No bank or mobile-money account',b:'No household member reports a bank or mobile-money account in the savings module.',color:C.navy},
  {x:832,k:'DOUBLE EXCLUSION',t:'Both gaps, among poor households',b:'A weighted descriptive measure of overlap, not proof of ineligibility or program failure.',color:C.orange}
 ];
 for(const c of cards){rect(s,c.x,174,348,300,C.pale,1,C.line);pill(s,c.k,c.x+22,198,190,C.aqua,c.color);text(s,c.t,c.x+24,250,300,70,24,C.ink,true);text(s,c.b,c.x+24,336,295,95,17,C.gray);}
 text(s,'Question for decision makers',70,518,290,30,17,C.teal,true);text(s,'Where should local teams check whether service access is falling short, and what barriers should they investigate?',70,552,1080,68,25,C.ink,true);
 note(s,'Definitions follow the EICV7 microdata modules. The survey does not observe household VUP eligibility. Source: NISR EICV7 catalog/questionnaire; authors’ calculations.');
}
// 3 — Data and method
{
 const s=base('EICV7 supports district level measurement','One nationally representative cross-section, summarized across Rwanda’s 30 districts.',3);
 const stats=[['15,054','households in analysis'],['30','districts'],['Oct 2023–Oct 2024','fieldwork']];
 stats.forEach((a,i)=>{const x=70+i*365;rect(s,x,158,325,112,C.pale,1,C.line);text(s,a[0],x+22,174,285,45,30,C.navy,true);text(s,a[1],x+23,220,280,28,15,C.gray);});
 const steps=[['1','Poverty','Population-weighted district poverty rates; checked against NISR published district benchmarks.'],['2','Coverage','Household weights for VUP participation and account access among poor households.'],['3','Overlap','Poor households with neither observed VUP participation nor a bank/mobile account.']];
 steps.forEach((a,i)=>{const y=320+i*88;rect(s,78,y,48,48,C.teal,1);text(s,a[0],78,y,48,48,22,C.white,true);text(s,a[1],152,y-1,202,35,20,C.ink,true);text(s,a[2],354,y-3,780,58,17,C.gray);});
 text(s,'Reliability check',78,596,160,24,14,C.teal,true);text(s,'District poverty estimates reproduce NISR’s published rates within 0.1 percentage point.',240,591,850,32,16,C.ink);
 note(s,'Sources: NISR EICV7 Main Indicators Report and microdata catalog. Analysis sample count and weighted estimates are calculated from the provided EICV7 files. Population poverty uses pop_wt; household coverage/overlap uses weight.');
}
// 4 — National findings
{
 const s=base('About 1 in 6 poor households has neither observed service','National weighted estimates from EICV7; descriptive and self-reported.',4);
 rect(s,70,157,430,410,C.navy,1);text(s,'17.5%',104,204,360,110,68,C.white,true);text(s,'of poor households',108,316,340,40,24,C.white,true);text(s,'estimated to have neither observed VUP participation nor bank/mobile account access',108,371,320,110,19,'#D6E1E8');text(s,'≈134,600 poor households',108,500,360,30,18,'#A9DADC',true);
 const ms=[['27.4%','population poverty rate'],['15.9%','VUP coverage among poor households'],['82.0%','bank/mobile account access among poor households']];
 ms.forEach((a,i)=>{const y=180+i*130;rect(s,548,y,620,102,C.pale,1,C.line);text(s,a[0],576,y+14,175,58,38,C.teal,true);text(s,a[1],772,y+18,350,57,20,C.ink,true);});
 text(s,'Access does not imply affordability, active use, or suitability.',550,592,620,32,15,C.gray,true);
 note(s,'Authors’ weighted calculations from EICV7. NISR reports national population poverty of 27.4% for 2023/24. VUP coverage combines five participation modules. Financial access requires at least one household member with a bank or mobile-money account. The estimated poor-household count uses household expansion weights.');
}
// 5 — District burden bars
{
 const s=base('The largest estimated burden is concentrated in five districts','Estimated number of poor households with double exclusion; household weighted.',5);
 const d=[['Kamonyi',12220,29.0],['Nyagatare',11569,22.2],['Nyanza',10133,28.1],['Gisagara',8398,21.5],['Ngoma',8085,29.6]];
 const x0=280,maxW=620,scale=maxW/13000;
 d.forEach((a,i)=>{const y=177+i*82;text(s,a[0],80,y+5,180,32,20,C.ink,true);rect(s,x0,y,maxW,30,C.pale,1);rect(s,x0,y,a[1]*scale,30,i<3?C.teal:C.navy,1);text(s,`${(a[1]/1000).toFixed(1)}k`,x0+a[1]*scale+12,y-1,80,32,17,C.ink,true);text(s,`${a[2].toFixed(1)}% of poor households`,955,y+2,225,27,14,C.gray);});
 rect(s,80,612,1090,1,C.line);text(s,'Rates and counts answer different planning questions: intensity vs. number of households.',82,624,1060,28,16,C.teal,true);
 note(s,'District burden is the sum of household survey weights for poor households classified as double-excluded. Top five based on EICV7 analysis output. Rounded counts and rates. These district rankings are estimates and carry sampling uncertainty.');
}
// 6 — Highest rates and uncertainty
{
 const s=base('The highest rates warrant local checks, with uncertainty in view','District estimates can guide questions; small samples and wide intervals limit ranking precision.',6);
 const d=[['Ngoma',29.6,20.9,38.3],['Kamonyi',29.0,20.8,37.1],['Nyanza',28.1,21.5,34.7],['Muhanga',25.9,12.5,39.3],['Huye',24.6,16.4,32.8]];
 d.forEach((a,i)=>{const y=176+i*73;text(s,a[0],80,y,160,34,19,C.ink,true);const xp=270,wp=560;rect(s,xp,y+13,wp,5,C.line,1);const lo=xp+a[2]/45*wp,hi=xp+a[3]/45*wp,m=xp+a[1]/45*wp;rect(s,lo,y+8,Math.max(4,hi-lo),15,'#A9DADC',1);rect(s,m-6,y+5,12,21,C.teal,1);text(s,`${a[1].toFixed(1)}%  (${a[2].toFixed(1)}–${a[3].toFixed(1)})`,860,y,300,34,16,C.ink,true);});
 text(s,'95% confidence intervals',270,552,330,24,13,C.muted);text(s,'Nyarugenge (35) and Kicukiro (40) have fewer than 50 sampled poor households.',80,598,1050,30,15,C.red,true);
 note(s,'Rates and approximate 95% confidence intervals calculated from the EICV7 district output. Variance uses stratified PSU-cluster ratio linearization and normal 1.96 multiplier; confirm against NISR survey-design documentation before publication. Poor-household sample sizes: Nyarugenge 35, Kicukiro 40.');
}
// 7 — Practical action and limits
{
 const s=base('Use the map to target service reviews, then verify the cause','Three steps for districts, social-protection teams and financial-service providers.',7);
 const actions=[
  ['1','Review together','Start with high-burden districts. Bring VUP teams, civil society and account providers together to check local service barriers.'],
  ['2','Assess and refer','Offer voluntary VUP eligibility checks and practical account information at accessible service points.'],
  ['3','Track overlap','Monitor protection reach and account access together; publish district summaries with uncertainty.']
 ];
 actions.forEach((a,i)=>{const x=70+i*380;rect(s,x,164,342,224,C.pale,1,C.line);rect(s,x+22,185,46,46,C.teal,1);text(s,a[0],x+22,185,46,46,21,C.white,true);text(s,a[1],x+84,187,230,38,21,C.ink,true);text(s,a[2],x+24,253,292,112,16,C.gray);});
 rect(s,70,426,1090,169,'#FFF7EE',1,'#F0D9BF');text(s,'Limits to keep in the decision',94,447,470,32,18,C.orange,true);text(s,'The survey does not establish eligibility, causes of non-coverage, affordability, active use or program impact. Treat the findings as a screening signal, and validate locally before changing eligibility or targeting individual households.',94,491,1015,80,18,C.ink);
 note(s,'Recommendations are proposed actions based on descriptive EICV7 findings, not causal impact estimates. Sources: NISR EICV7 microdata/catalog, Main Indicators Report, and authors’ calculations. District boundary layer source: Rwanda National Geodata / NISR and Rwanda Land Authority.');
}

const tmp=path.join(root,'.work','deck-build'); await fs.mkdir(tmp,{recursive:true});
for (const [i,s] of pres.slides.items.entries()) {
 const blob=await pres.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const candidate=path.join(tmp,'candidate.pptx'); await (await PresentationFile.exportPptx(pres)).save(candidate);
await fs.mkdir(path.join(root,'deliverables'),{recursive:true});
const buildStamp=new Date().toISOString().replaceAll(':','-').replaceAll('.','-');
const output=path.join(root,'deliverables',`rwanda_double_exclusion_presentation_${buildStamp}.pptx`);
const req={explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[]};
await finalizer.finalizePresentation({
 ...req,workspaceDir:root,candidatePath:candidate,finalPath:output,
 pythonExecutable:'C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:['Aptos']},verifyArtifactToolImport:true,
 receiptPath:path.join(tmp,'validation.json'),
});
console.log(output);
