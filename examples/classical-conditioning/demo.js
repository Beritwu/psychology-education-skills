/* MIT · PEBS contributors. Educational strings: CC BY-SA 4.0.
   Schematic events only: no measured response strengths or learning thresholds. */
"use strict";
const messages = {
  "zh-CN": {
    languageLabel:"语言",eyebrow:"示范课程 / 学习与行为",title:"同一个声音，为什么会有不同意义？",intro:"逐步观察经典条件作用的三个阶段。先预测，再揭示：声音、食物与反应之间发生了什么？",draft:"草稿—未通过 QA · 待真实教师复核",labTitle:"经典条件作用 · 时间序列",phases:["01 学习前","02 配对阶段","03 学习后测试"],cueTitle:"声音",foodTitle:"食物",responseTitle:"目标唾液反应",present:"出现",absent:"未出现",observed:"出现目标反应",notObserved:"未呈现目标反应",ns:"NS · 中性刺激",us:"US · 无条件刺激",ur:"UR · 无条件反应",cs:"CS · 条件刺激",cr:"CR · 条件反应",dash:"—",previous:"上一步",play:"播放",pause:"暂停",next:"下一步",reset:"重置",speedLabel:"播放速度",arrowNote:"箭头用于引导阅读顺序；只有当前高亮事件在此步骤出现。",motionNote:"默认不自动播放。秒数只控制演示速度，不表示真实实验时间。",reducedNote:"已检测到减少动态效果偏好；建议使用逐步查看或静态图。",questionTitle:"停下来想一想",question:"学习后只有声音出现，为什么它引发的反应叫 CR？请结合引发反应的刺激和学习历史解释。",limitTitle:"图示不等于数据",limit:"配对片段代表反复配对的阶段。一次播放不表示一次就能学会；图中没有真实次数、成功率或反应强度。",transcriptTitle:"静态逐步说明 / 无动画替代",resourceTitle:"配套材料与制作记录",links:["完整教案（中文）","学习者工作纸","教师答案","技能设计记录","静态图"],footer:"教学示意，无真实参与者、实验或教师评分。动画代码 MIT；教育内容 CC BY-SA 4.0。",
    steps:[
      ["学习前：声音单独出现","声音最初尚未与食物建立本例中的学习关系，不引发目标唾液反应；它仍可能引起注意。"],
      ["学习前：食物出现","食物作为 US 引发目标唾液反应 UR。先区分外界的刺激与个体的反应。"],
      ["配对阶段：声音先出现","先观察声音。此时食物还未出现；暂停并预测接下来会发生什么。"],
      ["配对阶段：随后出现食物","声音之后出现食物，食物引发唾液反应。这个片段代表配对过程中的一次呈现。"],
      ["配对阶段：回顾学习历史","声音与食物反复配对。此处不指定需要多少次，也不把动画进度当成学习强度。"],
      ["学习后测试：只出现声音","假设条件作用已经形成。现在只呈现声音 CS，食物没有出现。先预测目标反应。"],
      ["学习后测试：条件反应","在本例设定中，声音 CS 引发唾液反应 CR。名称取决于引发它的刺激和学习历史。"]
    ]
  },
  en:{languageLabel:"Language",eyebrow:"SAMPLE LESSON / LEARNING & BEHAVIOR",title:"One tone. A different meaning after learning.",intro:"Explore three phases of classical conditioning. Predict before revealing: how do the tone, food and response relate?",draft:"Draft demonstration · Teacher review pending",labTitle:"Classical conditioning · Event sequence",phases:["01 Before learning","02 Pairing phase","03 After-learning test"],cueTitle:"Tone",foodTitle:"Food",responseTitle:"Target salivation",present:"Present",absent:"Absent",observed:"Target response shown",notObserved:"Target response not shown",ns:"NS · Neutral stimulus",us:"US · Unconditioned stimulus",ur:"UR · Unconditioned response",cs:"CS · Conditioned stimulus",cr:"CR · Conditioned response",dash:"—",previous:"Previous",play:"Play",pause:"Pause",next:"Next",reset:"Reset",speedLabel:"Playback",arrowNote:"Arrows guide reading order; only highlighted events occur in the current step.",motionNote:"No autoplay. Seconds control the demonstration, not experimental timing.",reducedNote:"Reduced motion is enabled. Use individual steps or the static diagram.",questionTitle:"Pause and explain",question:"After learning, why is salivation elicited by the tone called a CR? Refer to the eliciting stimulus and learning history.",limitTitle:"A diagram is not data",limit:"The pairing segment represents repeated pairings. One playback does not mean one trial is sufficient. No measured trial count, success rate or response strength is shown.",transcriptTitle:"Static step-by-step transcript",resourceTitle:"Lesson materials and provenance",links:["Full lesson (Chinese)","Learner worksheet (Chinese)","Teacher key (Chinese)","Skill design record","Static diagram"],footer:"Schematic teaching example: no real participants, experiment or teacher scores. Code: MIT. Educational content: CC BY-SA 4.0.",steps:[
      ["Before learning: tone alone","The tone has not acquired the association in this example. It does not elicit the target salivation, although it may elicit attention."],
      ["Before learning: food","Food (US) elicits salivation (UR). Distinguish an event in the environment from the organism's response."],
      ["Pairing: tone first","Observe the tone before food appears. Pause and predict the next event."],
      ["Pairing: food follows","Food follows the tone and elicits salivation. This segment represents one presentation within the pairing phase."],
      ["Pairing: review the history","The tone and food are repeatedly paired. We specify neither the required trial count nor a learning-strength curve."],
      ["After learning: tone-alone test","Assume conditioning has developed. The tone (CS) appears alone; food is absent. Predict the target response."],
      ["After learning: conditioned response","In this scenario, the tone (CS) elicits salivation (CR). Labels depend on the eliciting stimulus and learning history."]
    ]},
  ja:{languageLabel:"言語",eyebrow:"授業サンプル / 学習と行動",title:"同じ音なのに、学習後は意味が変わる。",intro:"古典的条件づけの三段階を順に確認します。次の出来事を予測してから、音・食物・反応の関係を見てみましょう。",draft:"デモ草稿 · 教師による確認待ち",labTitle:"古典的条件づけ · 出来事の順序",phases:["01 学習前","02 対提示の段階","03 学習後のテスト"],cueTitle:"音",foodTitle:"食物",responseTitle:"対象となる唾液反応",present:"提示あり",absent:"提示なし",observed:"対象反応あり",notObserved:"対象反応の表示なし",ns:"NS · 中性刺激",us:"US · 無条件刺激",ur:"UR · 無条件反応",cs:"CS · 条件刺激",cr:"CR · 条件反応",dash:"—",previous:"前へ",play:"再生",pause:"一時停止",next:"次へ",reset:"最初から",speedLabel:"再生速度",arrowNote:"矢印は読む順序を示します。このステップで生じる出来事だけが強調されます。",motionNote:"自動再生はしません。秒数はデモの速度であり、実験の時間ではありません。",reducedNote:"動きを減らす設定を検出しました。ステップ表示や静的な図を利用できます。",questionTitle:"止めて、説明してみよう",question:"学習後に音が引き起こす唾液反応を、なぜ CR と呼ぶのでしょうか。刺激と学習の履歴を使って説明してください。",limitTitle:"図は測定データではありません",limit:"対提示の場面は繰り返しの過程を代表します。一度の再生で学習が成立するという意味ではありません。回数、成功率、反応強度の測定値は示していません。",transcriptTitle:"静的な説明を読む",resourceTitle:"教材と制作記録",links:["指導案（中国語）","ワークシート（中国語）","教師用解答（中国語）","スキル設計記録（英語）","静的な図"],footer:"実際の参加者・実験・教師評価を含まない教育用の模式例です。コード：MIT。教育内容：CC BY-SA 4.0。",steps:[
      ["学習前：音だけを提示","この例では音と食物の関連はまだ学習されていません。対象となる唾液反応は生じませんが、注意など別の反応はあり得ます。"],
      ["学習前：食物を提示","食物（US）が唾液反応（UR）を引き起こします。外界の出来事と個体の反応を区別しましょう。"],
      ["対提示：まず音","音が先に提示され、食物はまだありません。ここで止めて、次の出来事を予測します。"],
      ["対提示：続いて食物","音の後に食物が提示され、唾液反応を引き起こします。対提示段階の一場面です。"],
      ["対提示：学習の履歴を確認","音と食物が繰り返し対提示されます。必要な試行回数や学習の強さは示していません。"],
      ["学習後：音だけでテスト","条件づけが成立したと仮定します。音（CS）だけを提示し、食物は提示しません。反応を予測してください。"],
      ["学習後：条件反応","この設定では音（CS）が唾液反応（CR）を引き起こします。名称は誘発刺激と学習の履歴によって決まります。"]
    ]},
  ko:{languageLabel:"언어",eyebrow:"예제 수업 / 학습과 행동",title:"같은 소리, 학습 후에는 다른 의미.",intro:"고전적 조건형성의 세 단계를 차례로 살펴보세요. 먼저 예측한 뒤 소리, 먹이, 반응의 관계를 확인합니다.",draft:"시연용 초안 · 교사 검토 대기",labTitle:"고전적 조건형성 · 사건 순서",phases:["01 학습 전","02 짝짓기 단계","03 학습 후 검사"],cueTitle:"소리",foodTitle:"먹이",responseTitle:"관찰 대상 침 분비",present:"제시됨",absent:"제시되지 않음",observed:"대상 반응이 나타남",notObserved:"대상 반응을 표시하지 않음",ns:"NS · 중성 자극",us:"US · 무조건 자극",ur:"UR · 무조건 반응",cs:"CS · 조건 자극",cr:"CR · 조건 반응",dash:"—",previous:"이전",play:"재생",pause:"일시 정지",next:"다음",reset:"처음으로",speedLabel:"재생 속도",arrowNote:"화살표는 읽는 순서입니다. 현재 단계에서 일어나는 사건만 강조됩니다.",motionNote:"자동 재생하지 않습니다. 초 단위 시간은 시연 속도이며 실험 시간이 아닙니다.",reducedNote:"동작 줄이기 설정이 감지되었습니다. 단계별 보기나 정적 그림을 이용하세요.",questionTitle:"멈추고 설명해 보세요",question:"학습 후 소리가 일으키는 침 분비를 왜 CR이라고 할까요? 반응을 유발한 자극과 학습 이력을 함께 설명하세요.",limitTitle:"그림은 측정 자료가 아닙니다",limit:"짝짓기 장면은 반복되는 과정을 대표합니다. 한 번 재생했다고 한 번에 학습한다는 뜻이 아닙니다. 실제 횟수, 성공률, 반응 강도는 제시하지 않습니다.",transcriptTitle:"단계별 정적 설명 보기",resourceTitle:"수업 자료와 제작 기록",links:["전체 지도안 (중국어)","학습자 활동지 (중국어)","교사용 정답 (중국어)","스킬 설계 기록 (영어)","정적 그림"],footer:"실제 참여자, 실험 또는 교사 점수가 없는 교육용 모식 예제입니다. 코드: MIT. 교육 내용: CC BY-SA 4.0.",steps:[
      ["학습 전: 소리만 제시","이 예제에서는 소리와 먹이의 관계가 아직 학습되지 않았습니다. 대상 침 분비는 일어나지 않지만 주의와 같은 다른 반응은 있을 수 있습니다."],
      ["학습 전: 먹이 제시","먹이(US)가 침 분비(UR)를 일으킵니다. 환경의 사건과 개체의 반응을 구분하세요."],
      ["짝짓기: 소리가 먼저","먼저 소리가 나고 먹이는 아직 없습니다. 멈추고 다음 사건을 예측하세요."],
      ["짝짓기: 뒤이어 먹이","소리 뒤에 먹이가 제시되어 침 분비를 일으킵니다. 이 장면은 짝짓기 단계의 한 제시를 나타냅니다."],
      ["짝짓기: 학습 이력 확인","소리와 먹이를 반복해서 짝짓습니다. 필요한 시행 횟수나 학습 강도는 표시하지 않습니다."],
      ["학습 후: 소리만으로 검사","조건형성이 이루어졌다고 가정합니다. 소리(CS)만 있고 먹이는 없습니다. 대상 반응을 예측하세요."],
      ["학습 후: 조건 반응","이 설정에서는 소리(CS)가 침 분비(CR)를 일으킵니다. 이름은 유발 자극과 학습 이력에 따라 달라집니다."]
    ]}
};
const frames=[
  {phase:0,cue:true,food:false,response:false,cueTag:"ns",responseTag:"dash"},
  {phase:0,cue:false,food:true,response:true,cueTag:"ns",responseTag:"ur"},
  {phase:1,cue:true,food:false,response:false,cueTag:"ns",responseTag:"dash"},
  {phase:1,cue:false,food:true,response:true,cueTag:"ns",responseTag:"ur"},
  {phase:1,cue:false,food:false,response:false,cueTag:"ns",responseTag:"dash"},
  {phase:2,cue:true,food:false,response:false,cueTag:"cs",responseTag:"dash"},
  {phase:2,cue:true,food:false,response:true,cueTag:"cs",responseTag:"cr"}
];
const $=id=>document.getElementById(id);
let lang="zh-CN",step=0,timer=null;
const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
function stop(){if(timer!==null)window.clearInterval(timer);timer=null;$("play").textContent=messages[lang].play;$("play").setAttribute("aria-pressed","false");}
function render(){
  const t=messages[lang],f=frames[step];
  document.documentElement.lang=lang;document.title="PEBS · "+t.title;
  for(const id of ["languageLabel","eyebrow","title","intro","draft","labTitle","cueTitle","foodTitle","responseTitle","previous","next","reset","speedLabel","arrowNote","questionTitle","question","limitTitle","limit","transcriptTitle","resourceTitle","footer"])$(id).textContent=t[id];
  $("position").textContent=`${step+1} / ${frames.length}`;
  $("play").textContent=timer===null?t.play:t.pause;$("play").setAttribute("aria-pressed",String(timer!==null));
  $("previous").disabled=step===0;$("next").disabled=step===frames.length-1;
  $("phaseNav").setAttribute("aria-label",t.labTitle);
  document.querySelectorAll("[data-phase]").forEach((b,i)=>{b.textContent=t.phases[i];if(i===f.phase)b.setAttribute("aria-current","step");else b.removeAttribute("aria-current");});
  for(const id of ["cue","food","response"])$(id).classList.toggle("active",f[id]);
  $("cueState").textContent=f.cue?t.present:t.absent;$("foodState").textContent=f.food?t.present:t.absent;$("responseState").textContent=f.response?t.observed:t.notObserved;
  $("cueTag").textContent=t[f.cueTag];$("foodTag").textContent=t.us;$("responseTag").textContent=t[f.responseTag];
  $("stepTitle").textContent=t.steps[step][0];$("caption").textContent=t.steps[step][1];
  $("motionNote").textContent=reduced.matches?t.reducedNote:t.motionNote;
  $("transcriptList").replaceChildren(...t.steps.map(s=>{const li=document.createElement("li");const b=document.createElement("strong");b.textContent=s[0]+". ";li.append(b,document.createTextNode(s[1]));return li;}));
  const files=["course.zh-CN.md","worksheet.zh-CN.md","teacher-key.zh-CN.md","design-record.md","overview.svg"];
  $("resources").replaceChildren(...t.links.map((label,i)=>{const a=document.createElement("a");a.href=files[i];a.textContent=label;return a;}));
}
function play(){stop();if(step===frames.length-1)step=0;timer=window.setInterval(()=>{step++;if(step>=frames.length-1){step=frames.length-1;stop();}render();},Number($("speed").value));render();}
$("play").addEventListener("click",()=>{if(timer===null)play();else{stop();render();}});
$("next").addEventListener("click",()=>{stop();step=Math.min(step+1,frames.length-1);render();});
$("previous").addEventListener("click",()=>{stop();step=Math.max(step-1,0);render();});
$("reset").addEventListener("click",()=>{stop();step=0;render();});
$("language").addEventListener("change",e=>{stop();lang=e.target.value;render();});
$("speed").addEventListener("change",()=>{if(timer!==null)play();});
document.querySelectorAll("[data-phase]").forEach(b=>b.addEventListener("click",()=>{stop();step=[0,2,5][Number(b.dataset.phase)];render();}));
document.addEventListener("visibilitychange",()=>{if(document.hidden){stop();render();}});
reduced.addEventListener("change",()=>{stop();render();});
render();
