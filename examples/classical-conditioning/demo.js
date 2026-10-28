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
const lesson = {
 'zh-CN':{meta:'20 分钟 · 心理学入门',practiceLink:'进入互动练习 ↗',path:['理解目标','观察与预测','解释与迁移'],sceneLabel:'场景观察 · 无声演示',sceneState:'教学示意',observeLabel:'观察笔记',focusLabel:'现在关注',focus:['声音与食物分别会引发什么？先区分刺激和反应。','声音先出现，食物后出现。两段配对只是示意，不代表学习所需次数。','食物不在场。请把反应与当前声音和此前学习历史联系起来。'],timelineLabel:'拖动时间线，逐帧比较',practiceTitle:'看懂了？用解释来证明。',practiceIntro:'先独立判断，再看反馈。答对选项后，还要能说明由什么刺激引发了反应。',correct:'判断正确',again:'再比较一次',questions:[{title:'反复配对后，声音单独出现，引发唾液反应。此时声音与反应分别是什么？',options:['US → UR：无条件刺激与无条件反应','CS → CR：条件刺激与条件反应','NS → UR：中性刺激与无条件反应','CR → CS：条件反应与条件刺激'],feedback:['食物可以在本例中作为 US；这里呈现的是经过配对学习的声音。回到最后一阶段，确认食物是否出现。','声音通过学习成为 CS，它引发的目标唾液反应为 CR。判断不能只看“都是唾液”，还要看诱发刺激和学习历史。','声音起初是 NS，但题干已给出配对学习及声音单独引发反应，不能仍按学习前命名。','声音是环境中的刺激；唾液是个体反应。这里把两者的类别倒置了。']},{title:'把声音换成灯光。灯光起初不引发目标反应，配对学习后灯光单独引发该反应。哪种解释合适？',options:['所有灯光天生就是条件刺激','动画演示两次，所以两次一定学会','灯光由 NS 成为 CS；标签取决于学习历史'],feedback:['CS 不是灯光天生的属性。题目提供了特定的学习历史，才能作出这个判断。','演示中的次数不是实验数据，也没有给出形成学习所需的固定次数。','可以迁移的是命名规则：根据学习历史和当前诱发刺激判断。反应名称不能脱离情境。']}]},
 en:{meta:'20 min · Introductory psychology',practiceLink:'Try the questions ↗',path:['Set the goal','Observe & predict','Explain & transfer'],sceneLabel:'SCENE STUDY · SILENT',sceneState:'Schematic demonstration',observeLabel:'OBSERVATION NOTES',focusLabel:'FOCUS NOW',focus:['What does the tone elicit, and what does food elicit? Separate stimuli from responses.','The tone precedes food. The two illustrative pairings do not specify how many trials learning requires.','Food is absent. Relate the response to the current tone and the preceding learning history.'],timelineLabel:'Scrub to compare events',practiceTitle:'Understanding goes beyond the right letter.',practiceIntro:'Choose independently, then read the explanation. Name the eliciting stimulus and use the learning history.',correct:'Correct reasoning',again:'Compare again',questions:[{title:'After repeated pairings, the tone alone elicits salivation. What are the tone and its elicited response?',options:['US → UR: unconditioned stimulus and response','CS → CR: conditioned stimulus and response','NS → UR: neutral stimulus and unconditioned response','CR → CS: conditioned response and stimulus'],feedback:['Food is the US in this example. The present stimulus is a tone with a pairing history. Check whether food is present.','The learned tone is the CS; salivation elicited by it is the CR. Similar-looking responses can have different labels depending on the eliciting stimulus and history.','The tone started as neutral, but the scenario now specifies learning and a tone-elicited response. Use the current phase.','The tone is an environmental stimulus; salivation is a response. These categories have been reversed.']},{title:'Replace the tone with a light. Initially it does not elicit the target response; after pairing, the light alone does. Which explanation fits?',options:['All lights are naturally conditioned stimuli','Two animated pairings guarantee learning in two trials','The light changes from NS to CS through its learning history'],feedback:['CS is not an inherent property of light. It describes the stimulus in a particular learning history.','Animation repetitions are not experimental data or a guaranteed learning threshold.','Transfer the labeling rule: use the learning history and the current eliciting stimulus, not just appearances.']} ]},
 ja:{meta:'20分 · 心理学入門',practiceLink:'理解を確認する ↗',path:['目標を知る','観察と予測','説明と応用'],sceneLabel:'場面の観察 · 無音',sceneState:'教育用の模式図',observeLabel:'観察ノート',focusLabel:'注目する点',focus:['音と食物はそれぞれ何を引き起こしますか。刺激と反応を区別しましょう。','音の後に食物が現れます。二つの場面は例示であり、学習に必要な試行回数ではありません。','食物はありません。今の音と、これまでの学習の履歴から反応を説明しましょう。'],timelineLabel:'時間軸を動かして出来事を比較',practiceTitle:'正解だけでなく、理由を説明しよう。',practiceIntro:'まず自分で判断し、次に解説を確認します。反応を引き起こした刺激と学習の履歴を説明してください。',correct:'正しい判断です',again:'もう一度比較しましょう',questions:[{title:'繰り返し対提示した後、音だけで唾液反応が生じます。この音と反応の名称は？',options:['US → UR：無条件刺激と無条件反応','CS → CR：条件刺激と条件反応','NS → UR：中性刺激と無条件反応','CR → CS：条件反応と条件刺激'],feedback:['この例の US は食物です。今提示されているのは学習後の音です。食物の有無を確認してください。','学習後の音は CS、その音が引き起こす唾液反応は CR です。同じように見える反応も、刺激と履歴によって名称が変わります。','初めは NS でしたが、問題では学習後に音だけで反応が生じています。現在の段階で判断します。','音は外界の刺激、唾液は個体の反応です。二つのカテゴリーが逆です。']},{title:'音を光に置き換えます。最初は対象反応を起こさず、対提示による学習後は光だけで反応が生じます。適切な説明は？',options:['すべての光は生まれつき CS である','二回の動画表示で二試行の学習が保証される','学習の履歴により光が NS から CS になる'],feedback:['CS は光そのものの属性ではありません。特定の学習の履歴を踏まえた名称です。','アニメーションの回数は実験データでも、必要な試行回数でもありません。','応用するのは命名の原則です。現在の誘発刺激と学習の履歴を確認します。']}]},
 ko:{meta:'20분 · 심리학 입문',practiceLink:'이해 확인하기 ↗',path:['목표 확인','관찰과 예측','설명과 전이'],sceneLabel:'장면 관찰 · 무음',sceneState:'교육용 모식 장면',observeLabel:'관찰 노트',focusLabel:'지금 볼 것',focus:['소리와 먹이는 각각 무엇을 일으키나요? 자극과 반응을 구분하세요.','소리 다음에 먹이가 나타납니다. 두 짝짓기 장면은 예시이며 학습에 필요한 시행 횟수가 아닙니다.','먹이가 없습니다. 현재 소리와 이전 학습 이력을 연결해서 반응을 설명하세요.'],timelineLabel:'시간선을 움직여 사건 비교',practiceTitle:'정답을 고른 뒤, 이유도 설명하세요.',practiceIntro:'먼저 스스로 판단하고 해설을 읽으세요. 반응을 일으킨 자극과 학습 이력을 함께 설명합니다.',correct:'올바른 판단입니다',again:'다시 비교해 보세요',questions:[{title:'반복해서 짝지은 후 소리만으로 침 분비가 일어납니다. 이 소리와 반응은 무엇인가요?',options:['US → UR: 무조건 자극과 무조건 반응','CS → CR: 조건 자극과 조건 반응','NS → UR: 중성 자극과 무조건 반응','CR → CS: 조건 반응과 조건 자극'],feedback:['이 예제의 US는 먹이입니다. 지금 제시되는 것은 학습된 소리입니다. 먹이가 있는지 확인하세요.','학습된 소리는 CS이고 그 소리가 일으키는 침 분비는 CR입니다. 비슷한 반응도 유발 자극과 학습 이력에 따라 이름이 달라집니다.','처음에는 NS였지만 문제는 학습 후 소리만으로 반응이 나타난다고 설명합니다. 현재 단계로 판단하세요.','소리는 환경의 자극이고 침 분비는 개체의 반응입니다. 두 범주가 뒤바뀌었습니다.']},{title:'소리 대신 빛을 사용합니다. 처음에는 대상 반응이 없지만 짝짓기 학습 후 빛만으로 반응이 생깁니다. 적절한 설명은?',options:['모든 빛은 원래부터 CS이다','애니메이션 두 번이면 두 시행으로 반드시 학습한다','학습 이력에 따라 빛이 NS에서 CS가 된다'],feedback:['CS는 빛의 타고난 속성이 아닙니다. 특정 학습 이력에서 부여하는 이름입니다.','애니메이션 횟수는 실험 자료나 필요한 학습 횟수가 아닙니다.','전이할 것은 명명 규칙입니다. 현재 유발 자극과 학습 이력을 확인하세요.']} ]}
};
const $=id=>document.getElementById(id);
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
const stops=[0,6,12,16,20,24,28,36];
const answers=[null,null], correctAnswers=[1,2];
let lang='zh-CN',time=0,playing=false,last=null,frameId=null,lastCaption='';
const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
const smooth=v=>{v=clamp(v);return v*v*(3-2*v);};
function state(t){
 const phase=Math.min(2,Math.floor(t/12));
 let cue=false,food=false,response=false,foodStart=0,responseStart=0,index=0;
 if(phase===0){cue=t<4;food=t>=6&&t<11.5;foodStart=6;response=food&&t>=7;responseStart=7;index=t<6?0:1;}
 if(phase===1){cue=(t>=12&&t<16)||(t>=20&&t<21.5);food=(t>=16&&t<19.5)||(t>=21.5&&t<24);foodStart=t<20?16:21.5;response=food&&t>=foodStart+.7;responseStart=foodStart+.7;index=t<16?2:t<20?3:4;}
 if(phase===2){cue=true;response=t>=28;responseStart=28;index=response?6:5;}
 return {phase,cue,food,response,foodStart,responseStart,index};
}
function updateScene(){
 const f=state(time),t=messages[lang],l=lesson[lang],moving=!reduced.matches;
 $('scrubber').value=time;$('scrubber').setAttribute('aria-valuetext',`${Math.floor(time)} / 36; ${t.phases[f.phase]}`);
 $('clock').textContent=`00:${String(Math.floor(time)).padStart(2,'0')} / 00:36`;
 $('position').textContent=t.phases[f.phase];$('phaseNumber').textContent=String(f.phase+1).padStart(2,'0');
 document.querySelectorAll('[data-phase]').forEach((b,i)=>{if(i===f.phase)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});
 $('focusText').textContent=l.focus[f.phase];
 const capKey=lang+f.index;if(capKey!==lastCaption){$('stepTitle').textContent=t.steps[f.index][0];$('caption').textContent=t.steps[f.index][1];lastCaption=capKey;}
 const cueTag=f.phase===2?'cs':'ns',responseTag=f.response?(f.phase===2?'cr':'ur'):'dash';
 $('cueTag').textContent=t[cueTag];$('foodTag').textContent=f.food?t.us:t.absent;$('responseTag').textContent=t[responseTag];
 $('cueSvgText').textContent=(f.phase===2?'CS':'NS')+' · '+t.cueTitle;
 $('foodSvgText').textContent='US · '+t.foodTitle;
 $('responseSvgText').textContent=f.phase===2?'CS → CR':'US → UR';
 for(const k of ['cue','food','response'])$(k+'Event').classList.toggle('active',f[k]);
 $('speakerLight').setAttribute('fill',f.cue?'#8be0e0':'#6f929a');
 $('speakerCone').setAttribute('r',12+(f.cue&&moving?Math.sin(time*20)*1.4:0));
 for(let i=0;i<3;i++){const p=(time*1.2-i*.22)%1,progress=(p+1)%1;const wave=$('wave'+i);wave.setAttribute('opacity',f.cue?(moving?(1-progress)*.9:.75):0);wave.setAttribute('transform',moving?`translate(${progress*30} 0)`:'');}
 const enter=f.food?(moving?smooth((time-f.foodStart)/.7):1):0;
 $('foodObject').setAttribute('opacity',enter);$('foodObject').setAttribute('transform',`translate(${-210*(1-enter)} 0)`);$('foodLabel').setAttribute('opacity',enter);
 $('responseLabel').setAttribute('opacity',f.response?1:0);$('droplets').setAttribute('opacity',f.response?1:0);
 for(let i=0;i<3;i++){const p=((time-f.responseStart)*.7+i*.34)%1;const v=(p+1)%1;$('drop'+i).setAttribute('transform',moving?`translate(0 ${v*45})`:`translate(0 ${i*13})`);$('drop'+i).setAttribute('opacity',moving?1-v*.8:1);}
 $('dogHead').setAttribute('transform',moving&&f.cue?`rotate(${Math.sin(time*2)*1.1} 350 244)`:'');
 $('tail').setAttribute('transform',moving&&f.response?`rotate(${Math.sin(time*4)*3} 449 276)`:'');
 $('previous').disabled=time<=0;$('next').disabled=time>=36;
 $('scene').setAttribute('aria-label',t.steps[f.index].join('. '));
}
function stop(){playing=false;last=null;if(frameId!==null)cancelAnimationFrame(frameId);frameId=null;$('play').textContent='▶ '+messages[lang].play;$('play').setAttribute('aria-pressed','false');}
function tick(now){if(!playing)return;if(last!==null)time=Math.min(36,time+(now-last)/1000*Number($('speed').value));last=now;updateScene();if(time>=36){stop();return;}frameId=requestAnimationFrame(tick);}
function play(){if(time>=36)time=0;playing=true;last=null;$('play').textContent='Ⅱ '+messages[lang].pause;$('play').setAttribute('aria-pressed','true');frameId=requestAnimationFrame(tick);}
function seek(value){stop();time=clamp(Number(value),0,36);updateScene();}
function renderQuestions(){
 const l=lesson[lang];$('questions').replaceChildren(...l.questions.map((q,qi)=>{
  const card=document.createElement('article');card.className='question-card';
  const number=document.createElement('div');number.className='question-number';number.textContent=`0${qi+1} / ${l.path[qi===0?1:2]}`;
  const heading=document.createElement('h3');heading.textContent=q.title;
  const group=document.createElement('div');group.className='options';group.setAttribute('role','group');group.setAttribute('aria-label',q.title);
  q.options.forEach((label,oi)=>{const button=document.createElement('button');button.type='button';button.dataset.question=qi;button.dataset.option=oi;button.setAttribute('aria-pressed',String(answers[qi]===oi));const prefix=document.createElement('b');prefix.textContent=String.fromCharCode(65+oi);button.append(prefix,document.createTextNode(label));if(answers[qi]===oi)button.className=oi===correctAnswers[qi]?'selected correct':'selected';button.onclick=()=>{answers[qi]=oi;renderQuestions();const selected=document.querySelector(`[data-question="${qi}"][data-option="${oi}"]`);selected.focus({preventScroll:true});};group.append(button);});
  const feedback=document.createElement('p');feedback.className='feedback';feedback.id='feedback'+qi;feedback.setAttribute('role','status');if(answers[qi]!==null){const strong=document.createElement('strong');strong.textContent=answers[qi]===correctAnswers[qi]?l.correct:l.again;feedback.append(strong,document.createTextNode(q.feedback[answers[qi]]));}
  card.append(number,heading,group,feedback);return card;
 }));
}
function localize(){const t=messages[lang],l=lesson[lang];document.documentElement.lang=lang;document.title='PEBS · '+t.title;
 for(const id of ['languageLabel','eyebrow','title','intro','draft','labTitle','cueTitle','foodTitle','responseTitle','previous','next','reset','speedLabel','questionTitle','question','limitTitle','limit','transcriptTitle','resourceTitle','footer'])$(id).textContent=t[id];
 for(const id of ['meta','practiceLink','sceneLabel','sceneState','observeLabel','focusLabel','timelineLabel','practiceTitle','practiceIntro'])$(id).textContent=l[id];
 $('sceneTitle').textContent=t.labTitle;$('sceneDesc').textContent=t.intro;$('phaseNav').setAttribute('aria-label',t.labTitle);$('scrubber').setAttribute('aria-label',l.timelineLabel);
 document.querySelectorAll('[data-phase]').forEach((b,i)=>b.textContent=t.phases[i]);
 $('learningPath').replaceChildren(...l.path.map((v,i)=>{const e=document.createElement('span');e.dataset.number=i+1;e.textContent=v;return e;}));
 $('timelineChapters').replaceChildren(...t.phases.map(v=>{const e=document.createElement('span');e.textContent=v;return e;}));
 $('motionNote').textContent=reduced.matches?t.reducedNote:t.motionNote;
 $('transcriptList').replaceChildren(...t.steps.map(s=>{const li=document.createElement('li');const b=document.createElement('strong');b.textContent=s[0]+'. ';li.append(b,document.createTextNode(s[1]));return li;}));
 const files=['course.zh-CN.md','worksheet.zh-CN.md','teacher-key.zh-CN.md','design-record.md','overview.svg'];$('resources').replaceChildren(...t.links.map((v,i)=>{const a=document.createElement('a');a.href=files[i];a.textContent=v;return a;}));
 stop();renderQuestions();updateScene();}
$('play').onclick=()=>playing?stop():play();$('reset').onclick=()=>seek(0);
$('previous').onclick=()=>seek([...stops].reverse().find(v=>v<time-.1)??0);
$('next').onclick=()=>seek(stops.find(v=>v>time+.1)??36);
$('scrubber').addEventListener('input',e=>seek(e.target.value));
$('language').onchange=e=>{lang=e.target.value;localize();};
$('speed').onchange=()=>{last=null;};
document.querySelectorAll('[data-phase]').forEach(b=>b.onclick=()=>seek(Number(b.dataset.phase)*12));
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
reduced.addEventListener('change',()=>{stop();localize();});
localize();
