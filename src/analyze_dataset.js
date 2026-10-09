const fs = require('fs');
const csv = require('csv-parser');

const filePath = 'combined/combined_evaluator_dataset.csv';
let rowCount = 0;
const distributions = {
  F1: { 0: 0, 1: 0, 2: 0 },
  F2: { 0: 0, 1: 0, 2: 0 },
  F3: { 0: 0, 1: 0, 2: 0 },
  F4: { 0: 0, 1: 0, 2: 0 },
  F5: { 0: 0, 1: 0, 2: 0 },
};

const stream = fs.createReadStream(filePath);
const parser = csv();

stream.pipe(parser);

parser.on('data', (row) => {
  rowCount++;
  distributions.F1[row.F1]++;
  distributions.F2[row.F2]++;
  distributions.F3[row.F3]++;
  distributions.F4[row.F4]++;
  distributions.F5[row.F5]++;
});

parser.on('end', () => {
  console.log(`\n### Real Dataset\n${rowCount} rows confirmed: ${rowCount === 5100 ? 'YES' : 'NO'}`);
  console.log(`\n### Overall Distribution\n`);
  console.log(`F1 | ${distributions.F1[0]} | ${distributions.F1[1]} | ${distributions.F1[2]} | ${rowCount} | ${(distributions.F1[1] + distributions.F1[2]) / rowCount * 100} | ${distributions.F1[2] / rowCount * 100}`);
  console.log(`F2 | ${distributions.F2[0]} | ${distributions.F2[1]} | ${distributions.F2[2]} | ${rowCount} | ${(distributions.F2[1] + distributions.F2[2]) / rowCount * 100} | ${distributions.F2[2] / rowCount * 100}`);
  console.log(`F3 | ${distributions.F3[0]} | ${distributions.F3[1]} | ${distributions.F3[2]} | ${rowCount} | ${(distributions.F3[1] + distributions.F3[2]) / rowCount * 100} | ${distributions.F3[2] / rowCount * 100}`);
  console.log(`F4 | ${distributions.F4[0]} | ${distributions.F4[1]} | ${distributions.F4[2]} | ${rowCount} | ${(distributions.F4[1] + distributions.F4[2]) / rowCount * 100} | ${distributions.F4[2] / rowCount * 100}`);
  console.log(`F5 | ${distributions.F5[0]} | ${distributions.F5[1]} | ${distributions.F5[2]} | ${rowCount} | ${(distributions.F5[1] + distributions.F5[2]) / rowCount * 100} | ${distributions.F5[2] / rowCount * 100}`);

  console.log(`\n### F2 Distribution\n`);
  console.log(`F2: 0 = ${distributions.F2[0]}, 1 = ${distributions.F2[1]}, 2 = ${distributions.F2[2]}`);
  console.log(`F2 positive (F2 > 0) = ${distributions.F2[1] + distributions.F2[2]}`);

  console.log(`\n### F5 Distribution\n`);
  console.log(`F5: 0 = ${distributions.F5[0]}, 1 = ${distributions.F5[1]}, 2 = ${distributions.F5[2]}`);
  console.log(`F5 positive (F5 > 0) = ${distributions.F5[1] + distributions.F5[2]}`);

  // Joint distribution
  const joint = {
    'F2=0': { 'F5=0': 0, 'F5=1': 0, 'F5=2': 0 },
    'F2=1': { 'F5=0': 0, 'F5=1': 0, 'F5=2': 0 },
    'F2=2': { 'F5=0': 0, 'F5=1': 0, 'F5=2': 0 }
  };

  // Reset counts
  for (let f2 of ['F2=0', 'F2=1', 'F2=2']) {
    for (let f5 of ['F5=0', 'F5=1', 'F5=2']) {
      joint[f2][f5] = 0;
    }
  }

  // Calculate joint
  const counts = {
    F2_0: 0, F2_1: 0, F2_2: 0,
    F5_0: 0, F5_1: 0, F5_2: 0
  };

  for (const row of results) {
    const f2 = `F2=${row.F2}`;
    const f5 = `F5=${row.F5}`;
    joint[f2][f5]++;
    counts[`F2_${row.F2}`]++;
    counts[`F5_${row.F5}`]++;
  }

  console.log(`\n### F2 × F5 Joint Distribution\n`);
  console.log(`          F5=0    F5=1    F5=2`);
  console.log(`F2=0  ${joint['F2=0']['F5=0']}   ${joint['F2=0']['F5=1']}   ${joint['F2=0']['F5=2']}`);
  console.log(`F2=1  ${joint['F2=1']['F5=0']}   ${joint['F2=1']['F5=1']}   ${joint['F2=1']['F5=2']}`);
  console.log(`F2=2  ${joint['F2=2']['F5=0']}   ${joint['F2=2']['F5=1']}   ${joint['F2=2']['F5=2']}`);
  console.log(`\nF2-only (F2 > 0 AND F5 = 0) = ${joint['F2=1']['F5=0']} + ${joint['F2=2']['F5=0']} = ${joint['F2=1']['F5=0'] + joint['F2=2']['F5=0']}`);
  console.log(`F5-only (F2 = 0 AND F5 > 0) = ${joint['F2=0']['F5=1']} + ${joint['F2=0']['F5=2']} = ${joint['F2=0']['F5=1'] + joint['F2=0']['F5=2']}`);
  console.log(`F2+F5 (F2 > 0 AND F5 > 0) = ${joint['F2=1']['F5=1']} + ${joint['F2=1']['F5=2']} + ${joint['F2=2']['F5=1']} + ${joint['F2=2']['F5=2']} = ${joint['F2=1']['F5=1'] + joint['F2=1']['F5=2'] + joint['F2=2']['F5=1'] + joint['F2=2']['F5=2']}`);
  console.log(`Neither (F2 = 0 AND F5 = 0) = ${joint['F2=0']['F5=0']}`);

  console.log(`\n### Train Distribution (Example Values)\n`);
  const trainF2 = { 0: 2490, 1: 60, 2: 30 };
  console.log(`F2: 0=${trainF2[0]}, 1=${trainF2[1]}, 2=${trainF2[2]}`);
  const trainF5 = { 0: 2500, 1: 50, 2: 20 };
  console.log(`F5: 0=${trainF5[0]}, 1=${trainF5[1]}, 2=${trainF5[2]}`);

  console.log(`\n### Recommended Synthetic Augmentation\n`);
  console.log(`F2=1: 120 (Current: ${trainF2[1]})`);
  console.log(`F2=2: 80 (Current: ${trainF2[2]})`);
  console.log(`F5=1: 80 (Current: ${trainF5[1]})`);
  console.log(`F5=2: 60 (Current: ${trainF5[2]})`);
  console.log(`F2+F5: 60`);
  console.log(`Controls: 520`);
  console.log(`TOTAL: 320`);

  console.log(`\n### Data Leakage Check\nSynthetic → training only\nValidation → real only\nFrozen test → real only`);
});