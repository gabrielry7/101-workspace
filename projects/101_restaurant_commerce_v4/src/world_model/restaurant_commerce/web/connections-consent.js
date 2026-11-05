'use strict';
const state=new URLSearchParams(location.search).get('state');
if(state){for(const [id,params] of [['allow',{code:'synthetic-owner-grant'}],['deny',{error:'access_denied'}]])document.getElementById(id).href='/connections/google/callback?'+new URLSearchParams({state,...params});}
