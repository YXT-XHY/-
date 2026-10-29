import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../frontend/capture.js', import.meta.url), 'utf8');
const start = source.indexOf('  function wavBlob(');
const end = source.indexOf('  function quality(', start);
const scope = {Blob, ArrayBuffer, DataView, Math};
vm.runInNewContext(source.slice(start, end) + '\nthis.encode = wavBlob;', scope);
const blob = scope.encode(new Float32Array([-1, -.5, 0, .5, 1]), 48000);
const bytes = new DataView(await blob.arrayBuffer());
assert.equal(blob.type, 'audio/wav');
assert.equal(bytes.byteLength, 54);
assert.equal(bytes.getUint32(24, true), 48000);
assert.equal(bytes.getUint16(22, true), 1);
assert.equal(bytes.getUint16(34, true), 16);
assert.equal(bytes.getUint32(40, true), 10);
assert.deepEqual([0,1,2,3,4].map(i=>bytes.getInt16(44+i*2,true)), [-32768,-16384,0,16384,32767]);
console.log('PASS: PCM WAV header, mono format, sample rate, sample encoding');

let Processor;
const messages=[];
const workletScope = {
  AudioWorkletProcessor: class { constructor(){ this.port={postMessage:data=>messages.push(data)}; } },
  Float32Array,
  registerProcessor: (name, constructor)=>{ assert.equal(name,'pcm-collector');Processor=constructor; }
};
vm.runInNewContext(await readFile(new URL('../frontend/pcm-worklet.js', import.meta.url),'utf8'),workletScope);
const processor=new Processor();
assert.equal(processor.process([[new Float32Array([.5,.25]),new Float32Array([-.5,.25])]]),true);
processor.port.onmessage({data:'stop'});
assert.equal(messages.length,2);
assert.equal(messages[0].type,'pcm');
assert.deepEqual([...messages[0].chunk],[0,.25]);
assert.equal(messages[1].type,'stopped');
assert.equal(processor.process([]),false);
console.log('PASS: worklet mono downmix, buffered tail flush, stop acknowledgement');

const full=new Processor();messages.length=0;
for(let i=0;i<16;i++)full.process([[new Float32Array(128).fill(.3)]]);
assert.equal(messages.length,1);
assert.equal(messages[0].chunk.length,2048);
console.log('PASS: worklet streams bounded 2048-frame chunks');
