import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
synthetic=module('synthetic'); runner=module('run_champsim')
class Tools(unittest.TestCase):
    def test_all_workloads_deterministic_binary(self):
        self.assertGreater(len(synthetic.NAMES),12)
        for name in synthetic.NAMES:
            first=list(synthetic.events(name,40));self.assertEqual(first,list(synthetic.events(name,40)))
            self.assertEqual(len(first),80)
            for i,event in enumerate(first): self.assertEqual(len(synthetic.binary(event,i)),64)
    def test_manifest_integrity_and_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);synthetic.generate(out,100,2023)
            manifest=out/'manifest.json';self.assertEqual(len(runner.read_manifest(manifest,0,64)),16)
            with self.assertRaises(ValueError):runner.read_manifest(manifest,100,100)
            (out/'always_taken.champsimtrace').write_bytes(b'corrupted')
            with self.assertRaises(ValueError):runner.read_manifest(manifest,0,64)
    def test_reject_exhausted_trace_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'native.log'
            log.write_text('Warmup complete\nSimulation complete\n')
            runner.validate_log(log)
            # Native ChampSim may complete successfully after recycling its input.
            log.write_text('Warmup complete\n*** Reached end of trace: (0, "short.champsimtrace")\nSimulation complete\n')
            with self.assertRaisesRegex(ValueError, 'exhausted/recycled'):
                runner.validate_log(log)
    def test_roi_metric_extraction(self):
        data=[{'name':'Simulation','roi':{'cores':[{'instructions':1000,'cycles':500,'mispredict':{'conditional':5}}],
              'LLC':{'LOAD':{'hit':[7],'miss':[3]},'RFO':{'hit':[2],'miss':[1]},'miss latency':42.0}}}]
        result=runner.metrics(data);self.assertEqual(result['ipc'],2);self.assertEqual(result['branch_mpki'],5);self.assertEqual(result['llc_demand_misses'],4)
    def test_reject_bad_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace=Path(tmp)/'bad.txt';trace.write_text('B 4000 2\n')
            r=subprocess.run([str(ROOT/'build/bench'),str(trace)],capture_output=True)
            self.assertNotEqual(r.returncode,0)

class Selection(unittest.TestCase):
    def test_training_only_complete_grid(self):
        selector=module('select_config')
        rows=[{'split':'train','configuration':c,'workload':w,'ipc':ipc} for c,ipc in [('base','1'),('new','2')] for w in ['a','b']]
        self.assertEqual(selector.select(rows)[0],'new')
        rows[0]['split']='test'
        with self.assertRaises(ValueError):selector.select(rows)
        rows[0]['split']='train'
        with self.assertRaises(ValueError):selector.select(rows[:-1])

if __name__=='__main__':unittest.main()
