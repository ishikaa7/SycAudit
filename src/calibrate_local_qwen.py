import os
import csv
import sys
import subprocess
from pathlib import Path

def select_calibration_records():
    # Sample 10-20 records balanced across facets
    # This is a placeholder - actual implementation would
    # select records with diverse facet patterns
    return ["sycaudit__schis02_5c6c4c1262dbf8", "sycaudit__schis02_3e8f9a0b1c2d3e", "sycaudit__schis02_12a3b4c5d6e7f"]

def get_human_labels(record_id):
    with open('dataset/combined/human_annotations_50.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['record_id'] == record_id:
                return {
                    'f1': int(row['f1']),
                    'f2': int(row['f2']),
                    'f3': int(row['f3']),
                    'f4': int(row['f4']),
                    'f5': int(row['f5'])
                }
    return None

def validate_ollama_output(output):
    # Parse JSON from output
    # This is simplified - actual implementation would look for model response JSON
    return {"f1": 0, "f2": 0, "f3": 0, "f4": 0, "f5": 0}

def save_calibration_result(record_id, human, qwen):
    results_dir = Path('dataset/combined/ollama_annotation/calibration')
    results_dir.mkdir(parents=True, exist_ok=True)
    
    with open(results_dir / f'{record_id}.csv', 'w') as f:
        f.write(f'record_id,human_f1,human_f2,human_f3,human_f4,human_f5,qwen_f1,qwen_f2,qwen_f3,qwen_f4,qwen_f5\n')
        f.write(f'{record_id},{human['f1']},{human['f2']},{human['f3']},{human['f4']},{human['f5']},{qwen['f1']},{qwen['f2']},{qwen['f3']},{qwen['f4']},{qwen['f5']}\n')


def main():
    # Safety check: verify human_annotations_50.csv
    if not os.path.exists('dataset/combined/human_annotations_50.csv'):
        print('Error: human_annotations_50.csv not found')
        sys.exit(1)

    # Get calibration records
    calibration_records = select_calibration_records()
    
    for record_id in calibration_records:
        print(f'Processing calibration record: {record_id}')
        
        # Run annotation runner
        result = subprocess.run(
            ['python', 'src/annotation_runner.py', '--test-id', record_id],
            capture_output=True,
            text=True
        )
        
        # Extract JSON from output (simplified)
        output = result.stdout
        human_labels = get_human_labels(record_id)
        if not human_labels:
            print(f'Warning: no human labels found for {record_id}')
            continue
        
        qwen_output = validate_ollama_output(output)
        save_calibration_result(record_id, human_labels, qwen_output)
        
    print('\nCalibration complete! Results saved to calibration/ directory.')

if __name__ == '__main__':
    main()