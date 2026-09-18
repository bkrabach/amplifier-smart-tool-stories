// Narration is independent of writing-provider settings and pinned to a revision.
(() => {
  let target=null, operation=null, configuration=null, records=[], urls=[], exportAfter=false;
  let writingOperation=null, scriptId=null, scripts=[], writingDraft=null;
  const draftText=()=>JSON.stringify([...$('speechNotes').querySelectorAll('textarea')].map(e=>e.value));
  const scriptStatus=text=>{$('scriptStatus').textContent=text;};
  const status=text=>{$('speechStatus').textContent=text;};
  function draftKey(){return 'stories-narration-'+story.id+'-'+target;}
  function saveDraft(){sessionStorage.setItem(draftKey(),JSON.stringify([...$('speechNotes').querySelectorAll('textarea')].map(e=>e.value)));}
  function defaults(){
    const p=configuration.providers.find(p=>p.provider===$('speechProvider').value);
    $('speechModel').value=p.model;$('speechVoice').value=p.voice;
    availability();
  }
  function availability(){
    const p=configuration.providers.find(p=>p.provider===$('speechProvider').value);
    $('speechAvailability').textContent=(p.credential_present?'API key present; speech access has not been tested.':'Missing API key: '+p.credential_env.join(' or '))+(!configuration.model_access?' This viewer has no provider-use authority.':'');
  }
  async function apply(){
    await api('configure-narration',{provider:$('speechProvider').value,model:$('speechModel').value,voice:$('speechVoice').value,instructions:$('speechInstructions').value,request_id:requestId()});
  }
  async function audio(){
    urls.forEach(URL.revokeObjectURL);urls=[];$('speechAudio').replaceChildren();
    const n=records.find(n=>n.id===$('speechVersions').value);
    $('speechExport').disabled=!n||n.state!=='succeeded';
    if(!n)return;
    const label=document.createElement('p');label.textContent=`${n.settings.provider} · ${n.settings.model} · ${n.settings.voice} · ${n.state}`;$('speechAudio').append(label);
    if(['queued','running'].includes(n.state)){operation=n.operation_id;$('speechCancel').disabled=false;$('speechGenerate').disabled=true;$('speechGenerateExport').disabled=true;}
    for(const clip of n.clips){
      const r=await api('get-narration-audio',{narration_id:n.id,slide:clip.slide});
      if($('speechVersions').value!==n.id)return;
      const bytes=Uint8Array.from(atob(r.data_base64),c=>c.charCodeAt(0));
      const url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));urls.push(url);
      const p=document.createElement('p');p.textContent=`Slide ${clip.slide} · ${clip.duration_seconds.toFixed(1)} seconds · AI-generated voice: ${n.notes[clip.slide-1]}`;
      const player=document.createElement('audio');player.controls=true;player.src=url;player.preload='none';
      $('speechAudio').append(p,player);
    }
  }
  async function refresh(selected){
    const r=await api('list-narrations',{revision_id:target});records=r.narrations;
    const keep=selected||$('speechVersions').value;
    $('speechVersions').replaceChildren();
    for(const n of records){const o=document.createElement('option');o.value=n.id;o.textContent=`${n.id.slice(-8)} · ${n.state} · ${n.clips.length}/${n.notes.length} slides`;$('speechVersions').append(o);}
    if(records.some(n=>n.id===keep))$('speechVersions').value=keep;
    else if(records.length)$('speechVersions').value=records.at(-1).id;
    await audio();
  }
  $('narrationOpen').onclick=async()=>{
    try{
      if((operation || writingOperation) && target!==revision){$('narrationDialog').showModal();status('Narration is still running for the revision shown here. Finish or cancel before changing its target.');return;}
      if(target!==revision){scriptId=null;$('scriptStatus').textContent='';$('scriptDetails').textContent='';}
      target=revision;$('narrationRevision').textContent='Revision '+target;
      configuration=await api('narration-settings');
      const c=configuration.effective||{provider:'openai',...configuration.providers[0],instructions:''};
      $('speechProvider').value=c.provider;$('speechModel').value=c.model;$('speechVoice').value=c.voice;$('speechInstructions').value=c.instructions||'';availability();
      const r=await api('get-speaker-notes',{revision_id:target});
      let notes=r.notes;try{notes=JSON.parse(sessionStorage.getItem(draftKey()))||notes;}catch{}
      $('speechNotes').replaceChildren();
      notes.forEach((text,i)=>{const label=document.createElement('label');label.textContent=`Slide ${i+1}`;const field=document.createElement('textarea');field.rows=3;field.value=text;field.setAttribute('aria-label',`Narration for slide ${i+1}`);field.oninput=()=>{saveDraft();scriptStatus('Unsaved script edits; previous script review does not apply to this text.');};label.append(field);$('speechNotes').append(label);});
      $('narrationDialog').showModal();await refresh();scriptId=sessionStorage.getItem(draftKey()+'-script')||scriptId;await refreshScripts(null,true);
      const writing=await api('provider-settings');$('scriptWritingProvider').textContent='Writing provider: '+(writing.effective?.provider||'configured provider')+'. Preparing a script sends the deck, notes and retained sources to this provider; it does not generate audio.';
    }catch(e){error(e);}
  };
  function scriptInfo(s){
    $('scriptDetails').textContent=s?`${s.throughline} · Rough estimate ${s.estimated_seconds} seconds, not measured audio. ${s.review.method==='model_review'?'Model reviewed; not human approval.':'Not reviewed.'} ${s.limitations.join(' ')}`:'';
  }
  function loadScript(s){
    scriptId=s.id;sessionStorage.setItem(draftKey()+'-script',scriptId);const fields=[...$('speechNotes').querySelectorAll('textarea')];
    s.slides.forEach((row,i)=>{fields[i].value=row.text;});saveDraft();scriptInfo(s);$('scriptVersions').value=s.id;
  }
  async function refreshScripts(selected,autoLoad=false){
    scripts=(await api('list-narration-scripts',{revision_id:target})).scripts;
    $('scriptVersions').replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent='Current text / speaker notes';$('scriptVersions').append(empty);
    scripts.forEach((s,i)=>{const o=document.createElement('option');o.value=s.id;o.textContent=`Version ${i+1} · ${s.origin==='model'?'Prepared':'Edited'} · ~${s.estimated_seconds}s`;$('scriptVersions').append(o);});
    $('scriptVersions').value=selected||scriptId||'';
    scriptInfo(scripts.find(s=>s.id===scriptId));
    if(autoLoad&&!scriptId&&!sessionStorage.getItem(draftKey())&&scripts.length)loadScript(scripts.at(-1));
  }
  async function saveScript(){
    const old=scripts.find(s=>s.id===scriptId);
    if(old&&JSON.stringify(old.slides.map(s=>s.text))===draftText())return;
    const r=await api('save-narration-script',{revision_id:target,notes:JSON.parse(draftText()),base_script_id:scriptId,request_id:requestId()});
    scriptId=r.script_id;sessionStorage.setItem(draftKey()+'-script',scriptId);await refreshScripts(scriptId);scriptInfo(scripts.find(s=>s.id===scriptId));
  }
  $('scriptVersions').onchange=()=>{const s=scripts.find(s=>s.id===$('scriptVersions').value);if(s)loadScript(s);else{scriptId=null;sessionStorage.removeItem(draftKey()+'-script');scriptInfo(null);}};
  $('scriptSave').onclick=async()=>{try{await saveScript();scriptStatus('Script saved. No model or speech request.');}catch(e){scriptStatus(e.message);}};
  $('scriptPrepare').onclick=async()=>{
    $('scriptPrepare').disabled=true;
    try{
      saveDraft();writingDraft=draftText();
      const r=await api('prepare-narration',{revision_id:target,base_script_id:scriptId,draft_notes:JSON.parse(writingDraft),guidance:$('scriptGuidance').value,target_seconds:$('scriptDuration').value?Number($('scriptDuration').value):null,grant:{max_operations:1,timeout_seconds:180,max_output_tokens:12000},request_id:requestId()});
      writingOperation=r.operation_id;$('scriptCancel').disabled=false;$('scriptVersions').disabled=true;scriptStatus('Writing queued. No speech synthesis.');
    }catch(e){$('scriptPrepare').disabled=false;scriptStatus(e.message);}
  };
  $('scriptCancel').onclick=async()=>{try{await api('cancel-operation',{operation_id:writingOperation});scriptStatus('Writing cancellation requested.');}catch(e){scriptStatus(e.message);}};
  setInterval(async()=>{
    if(!writingOperation)return;
    try{
      const o=await api('get-operation',{operation_id:writingOperation});scriptStatus(o.state+(o.error?' · '+o.error.message:''));
      if(!['queued','running'].includes(o.state)){
        writingOperation=null;$('scriptPrepare').disabled=false;$('scriptCancel').disabled=true;$('scriptVersions').disabled=false;
        await refreshScripts();
        if(o.state==='succeeded'){
          const s=scripts.find(s=>s.id===o.result.script_id);
          if(writingDraft===draftText()){loadScript(s);scriptStatus('Script ready to review, edit, or synthesize. No audio generated.');}
          else scriptStatus('New script retained in the version list. Your newer text edits were preserved.');
        }
      }
    }catch(e){scriptStatus(e.message);}
  },1500);
  $('narrationClose').onclick=()=>{$('speechAudio').querySelectorAll('audio').forEach(a=>a.pause());$('narrationDialog').close();};
  $('speechProvider').onchange=defaults;
  $('speechApply').onclick=async()=>{try{await apply();status('Narration settings saved. No speech generated.');}catch(e){status(e.message);}};
  $('speechVersions').onchange=()=>audio().catch(e=>status(e.message));
  async function generate(andExport){
    exportAfter=andExport;
    $('speechGenerate').disabled=true;$('speechGenerateExport').disabled=true;
    try{
      saveDraft();await saveScript();await apply();
      const r=await api('generate-narration',{revision_id:target,script_id:scriptId,grant:{max_requests:12,max_characters:48000,timeout_seconds:300},request_id:requestId(),retry_uncertain:$('speechRetry').checked});
      operation=r.operation_id;$('speechCancel').disabled=false;status('Narration queued.');await refresh(r.narration_id);
    }catch(e){status(e.message);$('speechGenerate').disabled=false;$('speechGenerateExport').disabled=false;exportAfter=false;}
  }
  $('speechGenerate').onclick=()=>generate(false);
  $('speechGenerateExport').onclick=()=>generate(true);
  $('speechCancel').onclick=async()=>{try{await api('cancel-operation',{operation_id:operation});status('Cancellation requested; completed audio remains retained.');}catch(e){status(e.message);}};
  setInterval(async()=>{
    if(!operation)return;
    try{const o=await api('get-operation',{operation_id:operation});status(`${o.state}${o.progress?' · '+o.progress.completed_slides+'/'+o.progress.total_slides+' slides':''}${o.error?' · '+o.error.message:''}`);
      if(!['queued','running'].includes(o.state)){operation=null;$('speechGenerate').disabled=false;$('speechGenerateExport').disabled=false;$('speechCancel').disabled=true;await refresh(o.result?.narration_id);if(exportAfter&&o.state==='succeeded')$('speechExport').click();exportAfter=false;}
    }catch(e){status(e.message);}
  },1500);
  $('speechExport').onclick=async()=>{
    const n=records.find(n=>n.id===$('speechVersions').value);if(!n)return;
    $('speechExport').disabled=true;$('speechExportStatus').textContent='Encoding from retained audio…';
    try{
      const delivery=$('speechDelivery').value;
      const r=await fetch('/api/narrated-download',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({revision_id:target,narration_id:n.id,delivery,pause_seconds:Number($('speechPause').value)})});
      if(!r.ok){const v=await r.json();throw Error(v.error?.message||'Export failed');}
      const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='narrated-story.'+(delivery==='separate'?'zip':'mp4');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      $('speechExportStatus').textContent='Export complete. No new speech synthesis.';
    }catch(e){$('speechExportStatus').textContent=e.message;}
    finally{$('speechExport').disabled=false;}
  };
})();
