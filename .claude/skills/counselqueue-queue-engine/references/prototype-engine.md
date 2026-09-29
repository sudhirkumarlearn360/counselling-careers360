# Prototype engine (reference only — PRD and SKILL.md win)

From `CounselQueue — staff console.html`. Divergences are listed in ../SKILL.md.

```js
function avgSession(cid){
  const done = S.students.filter(s=>s.counsellorId===cid && s.status==="done" && s.startAt && s.endAt);
  if(!done.length) return (co(cid)||{avg:15}).avg*MIN;
  return done.reduce((a,s)=>a+(s.endAt-s.startAt),0)/done.length;
}
function etaFor(s){
  const q = queueFor(s.counsellorId);
  const pos = q.findIndex(x=>x.id===s.id);
  if(pos<0) return {pos:0, eta:0};
  const cur = currentOf(s.counsellorId);
  const avg = avgSession(s.counsellorId);
  let remaining = 0;
  if(cur && cur.startAt) remaining = Math.max(2*MIN, avg-(now()-cur.startAt)); else if(cur) remaining = avg;
  return {pos:pos+1, eta: remaining + pos*avg};
}

/* pick counsellor with the lightest load for a stream */
function assignCounsellor(eventId, stream){
  const pool = eventCounsellors(eventId).filter(c=>c.status!=="offline");
  const match = pool.filter(c=>c.streams.includes(stream));
  const cands = (match.length?match:pool).filter(c=>c.status==="active");
  const final = cands.length?cands:(match.length?match:pool);
  if(!final.length) return null;
  return final.map(c=>({c, load:queueFor(c.id).length + (currentOf(c.id)?1:0)}))
              .sort((a,b)=>a.load-b.load || avgSession(a.c.id)-avgSession(b.c.id))[0].c;
}
function nextToken(eventId, stream){
  S.seq[eventId] = (S.seq[eventId]||0)+1;
  return stream+"-"+pad2(S.seq[eventId]);
}
function sendWA(to, txt){
  if(!S.settings.waEnabled) return;
  S.wa.unshift({t:now(), to, txt, profile:{course:"B.Des / fashion design", exams:["None / not sure"], clarity:"Completely confused", help:["Course selection", "College & course comparison"]}});
  S.wa = S.wa.slice(0,60);
}
function toast(msg, kind){
  const el = document.createElement("div");
  el.className = "toast"+(kind?" "+kind:"");
  el.textContent = msg;
  document.getElementById("toasts").appendChild(el);
  setTimeout(()=>{ el.style.opacity="0"; el.style.transition="opacity .4s"; setTimeout(()=>el.remove(),400); }, 3200);
}
</script>
<script>
"use strict";
/* ---------------- actions ---------------- */
function checkIn(data, source){
  const e = ev(data.eventId);
  const dupe = S.students.find(s=>s.phone===data.phone && s.eventId===data.eventId &&
    ["waiting","called","in_session"].includes(s.status));
  if(dupe) return {error:"A token is already open for this number — "+dupe.token+". Ask reception to reopen it.", student:dupe};
  const c = assignCounsellor(data.eventId, data.stream);
  if(!c) return {error:"No counsellor is on duty for this centre yet. Reception can add you manually."};
  const s = {
    id:uid("s_"), token:nextToken(data.eventId, data.stream), name:data.name, phone:data.phone,
    email:data.email, stream:data.stream, klass:data.klass, school:data.school||"",
    parentPhone:data.parentPhone||"", eventId:data.eventId, counsellorId:c.id,
    status:"waiting", consent: source==="qr" ? "given":"pending", source, checkinAt:now(),
    calledAt:null, startAt:null, endAt:null, recalls:0, notes:[], feedback:null,
    profile:{city:e?e.city:"", course:data.course||"", exams:data.exams||[],
             clarity:data.clarity||"", help:data.help||[], streamOther:data.streamOther||""}
  };
  S.students.push(s);
  if(source==="reception")
    sendWA(s.phone, `Careers360 ${e?e.city:""}: our front desk has checked you in. Token ${s.token}, counsellor ${c.name} at ${c.desk}. Reply YES to confirm it's you and allow us to use these details for counselling.`);
  else
    sendWA(s.phone, `Careers360 ${e?e.city:""}: you're in the queue. Token ${s.token}, counsellor ${c.name} at ${c.desk}. Keep this chat open — we'll message you when your turn is near.`);
  save();
  return {student:s};
}
function callToken(cid, token){
  const s = S.students.find(x=>x.token.toLowerCase()===String(token).trim().toLowerCase() && x.eventId===co(cid).eventId);
  if(!s) return {error:"No token "+token+" at this centre today."};
  if(s.status==="done") return {error:"Token "+s.token+" was already counselled at "+fmtTime(s.endAt)+"."};
  if(s.counsellorId!==cid){
    s.counsellorId = cid;
    sendWA(s.phone, `Your counsellor changed to ${co(cid).name}, ${co(cid).desk}.`);
  }
  s.status="called"; s.calledAt=now();
  sendWA(s.phone, `It's your turn. Please go to ${co(cid).desk} — ${co(cid).name}. Reply YES to confirm you're here and consent to your details being used for counselling.`);
  save(); return {student:s};
}
function callNext(cid){
  const q = queueFor(cid);
  if(!q.length) return {error:"Queue is empty."};
  return callToken(cid, q[0].token);
}
function startSession(id){ const s=st(id); s.status="in_session"; s.startAt=now(); save(); }
function endSession(id){
  const s=st(id); s.status="done"; s.endAt=now();
  sendWA(s.phone, `Thanks for meeting ${co(s.counsellorId).name}. Your shortlist and next steps are on the way. Rate this session 1-5?`);
  save();
}
function markNoShow(id){
  const s=st(id); s.recalls=(s.recalls||0)+1;
  if(s.recalls>=S.settings.recallLimit){ s.status="no_show"; sendWA(s.phone,`We called ${s.token} ${s.recalls} times. Visit the help desk to get back in the queue.`); }
  else { s.status="waiting"; s.checkinAt=now(); s.calledAt=null;
    sendWA(s.phone,`We called ${s.token} and missed you. You're back in the queue — next call is the last one.`); }
  save();
}
function requeue(id){ const s=st(id); s.status="waiting"; s.checkinAt=now(); s.calledAt=null; s.recalls=0; save(); }
function giveConsent(id){ const s=st(id); s.consent="given"; save(); }
function addNote(id, by, txt){ st(id).notes.push({t:now(), by, txt}); save(); }
function moveToTop(id){ const s=st(id); const q=queueFor(s.counsellorId); if(q[0]) s.checkinAt=q[0].checkinAt-1000; save(); }
function reassign(id, cid){ const s=st(id); s.counsellorId=cid; s.status="waiting"; s.calledAt=null;
  sendWA(s.phone, `You've been moved to ${co(cid).name}, ${co(cid).desk}. Token ${s.token} stays the same.`); save(); }

/* ---------------- tiny QR-ish glyph (decorative, deterministic) ---------------- */
```
