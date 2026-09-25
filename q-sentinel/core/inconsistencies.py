import math
import numpy as np

MEASUREMENT_EXPLANATIONS = {
    'Bit bias': {
        'name': 'Bit Bias',
        'formula': 'bias = fraction_of_ones - 0.5',
        'how_measured': 'Calculates the proportion of ones across the window and subtracts 0.5. Evaluated against calibrated baseline mean and variance.',
        'evidence_text': 'The observed zero/one balance differs significantly from the calibrated reference baseline (|z| >= 3 or persistent shift).',
        'recommended_check': 'Inspect detector balance, optical beam splitters, and comparator/digitization threshold voltages for DC offset or thermal drift.',
        'disclaimer': 'The displayed bit slice is an inspection sample from the affected window; statistical bias does not assert that individual bits are physically defective.'
    },
    'Serial correlation': {
        'name': 'Serial Correlation',
        'formula': 'autocorrelation = Cov(x_t, x_{t+1}) / Var(x_t)',
        'how_measured': 'Compares each bit with the subsequent bit at lag 1. Measures memory or serial dependence in the output stream.',
        'evidence_text': 'Lag-1 autocorrelation deviates from zero beyond calibrated decision boundaries, indicating inter-symbol interference or memory.',
        'recommended_check': 'Inspect detector recovery time, pulse pile-up, clock synchronization, bandwidth filtering, and digitization latch timing.',
        'disclaimer': 'Serial correlation reflects statistical transition probabilities across adjacent bits, not individual bit corruption.'
    },
    'Periodic pattern': {
        'name': 'Periodic Pattern',
        'formula': 'spectral_peak = max_{k} |DFT(x)[k]| normalized by 95% threshold',
        'how_measured': 'Computes the Discrete Fourier Transform (DFT) across the window to detect discrete frequency spikes exceeding theoretical white-noise levels.',
        'evidence_text': 'One or more spectral frequency components exceed expected limits, indicating harmonic contamination or periodic clock leakage.',
        'recommended_check': 'Inspect power supply ripple, RF/EMI shielding, clock feedthrough, and periodic sampling clock jitter.',
        'disclaimer': 'Periodicity is a global property of the window frequency spectrum; specific bit positions represent illustrative phase slices.'
    },
    'Burst error': {
        'name': 'Burst Error',
        'formula': 'longest_run = max continuous streak of identical bits',
        'how_measured': 'Measures maximum contiguous streaks of identical zeros or ones within the window and localized outlier density.',
        'evidence_text': 'A localized sub-sequence contains an unusually long stuck run or abnormal bit concentration inconsistent with IID distribution.',
        'recommended_check': 'Inspect detector blind times, dead-time afterpulsing, cosmic ray / optical flash transients, or buffer underrun/overrun events.',
        'disclaimer': 'The flagged bit range marks the contiguous streak or burst interval observed in the digitized stream.'
    },
    'Repeated sequence': {
        'name': 'Repeated Sequence',
        'formula': 'repetition = fraction of matching adjacent 32-bit words',
        'how_measured': 'Segments the window into 32-bit blocks and compares consecutive blocks for duplicate patterns or rolling substring matches.',
        'evidence_text': 'The same binary sequence or word repeats consecutively or with high frequency within the window.',
        'recommended_check': 'Inspect FIFO read/write pointers, DMA transfer corruption, state machine reset loops, and post-processing ring buffers.',
        'disclaimer': 'Repeated sequences represent matching block boundaries identified in the window.'
    },
    'Sudden collapse': {
        'name': 'Entropy Collapse',
        'formula': 'shannon_loss = baseline_entropy - observed_shannon',
        'how_measured': 'Calculates empirical Shannon marginal entropy, min-entropy (-log2 max(p, 1-p)), and collision entropy (-log2(p^2 + (1-p)^2)).',
        'evidence_text': 'Marginal and min-entropy drop sharply below calibrated thresholds, indicating a severe reduction in unpredictable states.',
        'recommended_check': 'Inspect quantum source emission (laser/SPDC pump power, avalanche diode bias), optical alignment, and detector coupling.',
        'disclaimer': 'Entropy collapse is an aggregate measure of symbol distribution; individual bits remain valid binary symbols.'
    },
    'Gradual drift': {
        'name': 'Gradual Drift',
        'formula': 'Theil-Sen robust slope over sliding history & Spearman correlation < -0.6',
        'how_measured': 'Fits a robust non-parametric Theil-Sen slope over consecutive monitoring windows to detect slow monotonic degradation.',
        'evidence_text': 'Health score and entropy metrics exhibit consistent monotonic downward trajectory crossing operational early warning thresholds.',
        'recommended_check': 'Inspect laser diode aging, component temperature drift, photodetector dark count elevation, and optical attenuation degradation.',
        'disclaimer': 'Drift describes a multi-window trend trajectory rather than isolated point defects.'
    },
    'Mixed failure': {
        'name': 'Mixed Failure',
        'formula': 'combined_score = min(top_2_signatures)',
        'how_measured': 'Evaluates simultaneous elevated deviations across two or more orthogonal failure categories (e.g. bias plus correlation).',
        'evidence_text': 'Multiple independent statistical metrics exhibit anomalous shifts concurrently, suggesting compound physical deterioration.',
        'recommended_check': 'Perform comprehensive physical inspection of quantum source, detector bias circuits, temperature stabilization, and digitization logic.',
        'disclaimer': 'Mixed signatures reflect multiple concurrent statistical anomalies requiring multi-point diagnostic inspection.'
    },
    'Unknown / unclassified': {
        'name': 'Unknown / Unclassified',
        'formula': 'residual_deviation = max(0, 100 - max(signatures))',
        'how_measured': 'Detects significant deviation from baseline that does not match predefined signature profiles in the diagnostic library.',
        'evidence_text': 'Statistically anomalous behavior detected by CUSUM or NIST tests without a dominant matching failure pattern.',
        'recommended_check': 'Inspect raw acquisition logs, environmental sensor telemetry, and run comprehensive offline diagnostic test suites.',
        'disclaimer': 'An unclassified anomaly indicates departure from baseline without a specific archetype match.'
    }
}

# Aliases for flexible type lookup
TYPE_ALIASES = {
    'bias': 'Bit bias',
    'bit bias': 'Bit bias',
    'correlation': 'Serial correlation',
    'serial correlation': 'Serial correlation',
    'periodicity': 'Periodic pattern',
    'periodic': 'Periodic pattern',
    'periodic pattern': 'Periodic pattern',
    'burst': 'Burst error',
    'burst error': 'Burst error',
    'burst noise': 'Burst error',
    'repetition': 'Repeated sequence',
    'repeated sequence': 'Repeated sequence',
    'entropy collapse': 'Sudden collapse',
    'sudden collapse': 'Sudden collapse',
    'collapse': 'Sudden collapse',
    'drift': 'Gradual drift',
    'gradual drift': 'Gradual drift',
    'mixed': 'Mixed failure',
    'mixed failure': 'Mixed failure',
    'unknown': 'Unknown / unclassified',
    'unknown / unclassified': 'Unknown / unclassified',
}

def get_measurement_info(sig_type):
    canonical = TYPE_ALIASES.get(sig_type.lower().strip(), 'Unknown / unclassified')
    return MEASUREMENT_EXPLANATIONS.get(canonical, MEASUREMENT_EXPLANATIONS['Unknown / unclassified'])

def find_localized_ranges(row, window_bits=None, size=10000):
    """Identify localized anomalous bit ranges in a window (e.g. stuck runs, repeating blocks, or concentrated deviation)."""
    # Healthy windows do not have flagged ranges
    if row.get('state') in ['Healthy', 'Calibrating']:
        return []
        
    ranges = []
    window_num = row.get('window', 1)
    base_offset = row.get('bit_offset', (window_num - 1) * size)
    
    if window_bits is not None and len(window_bits) > 0:
        bits_arr = np.asarray(window_bits, dtype=np.uint8)
        
        # 1. Check for stuck streak (burst error / stuck bits)
        if len(bits_arr) > 1:
            diffs = np.diff(bits_arr)
            change_indices = np.where(diffs != 0)[0] + 1
            run_starts = np.r_[0, change_indices]
            run_ends = np.r_[change_indices, len(bits_arr)]
            run_lengths = run_ends - run_starts
            
            max_idx = np.argmax(run_lengths)
            max_len = run_lengths[max_idx]
            
            if max_len >= 8 or row.get('longest_streak', 0) >= 16:
                loc_start = int(run_starts[max_idx])
                loc_end = int(run_ends[max_idx] - 1)
                val = int(bits_arr[loc_start])
                ranges.append({
                    'start': base_offset + loc_start,
                    'end': base_offset + loc_end,
                    'local_start': loc_start,
                    'local_end': loc_end,
                    'length': int(max_len),
                    'window': window_num,
                    'type': 'Stuck streak',
                    'reason': f'Contiguous streak of {max_len} consecutive {val}s (longest run in window).'
                })
        
        # 2. Check for repeating 32-bit blocks
        num_blocks = len(bits_arr) // 32
        if num_blocks > 1 and not ranges:
            packed_blocks = [bits_arr[b*32:(b+1)*32].tobytes() for b in range(num_blocks)]
            repeat_count = 0
            repeat_start = None
            for b in range(len(packed_blocks) - 1):
                if packed_blocks[b] == packed_blocks[b+1]:
                    if repeat_start is None:
                        repeat_start = b * 32
                    repeat_count += 1
                else:
                    if repeat_start is not None and repeat_count >= 1:
                        loc_start = repeat_start
                        loc_end = (b + 1) * 32 - 1
                        ranges.append({
                            'start': base_offset + loc_start,
                            'end': base_offset + loc_end,
                            'local_start': loc_start,
                            'local_end': loc_end,
                            'length': loc_end - loc_start + 1,
                            'window': window_num,
                            'type': 'Repeated block sequence',
                            'reason': f'{repeat_count + 1} identical consecutive 32-bit blocks.'
                        })
                        repeat_start = None
                        repeat_count = 0
            if repeat_start is not None and repeat_count >= 1:
                loc_start = repeat_start
                loc_end = len(packed_blocks) * 32 - 1
                ranges.append({
                    'start': base_offset + loc_start,
                    'end': base_offset + loc_end,
                    'local_start': loc_start,
                    'local_end': loc_end,
                    'length': loc_end - loc_start + 1,
                    'window': window_num,
                    'type': 'Repeated block sequence',
                    'reason': f'{repeat_count + 1} identical consecutive 32-bit blocks.'
                })
    
        # 3. If no streak/repetition localized, isolate the 64-bit block with peak statistical deviation
        if not ranges:
            block_size = min(64, len(bits_arr))
            stride = 16
            best_idx = 0
            best_dev = -1.0
            for idx in range(0, len(bits_arr) - block_size + 1, stride):
                sub = bits_arr[idx:idx+block_size]
                dev = abs(float(np.mean(sub)) - 0.5)
                if dev > best_dev:
                    best_dev = dev
                    best_idx = idx
            ranges.append({
                'start': base_offset + best_idx,
                'end': base_offset + best_idx + block_size - 1,
                'local_start': best_idx,
                'local_end': best_idx + block_size - 1,
                'length': block_size,
                'window': window_num,
                'type': 'Flagged inspection region',
                'reason': f'Concentrated statistical deviation within window {window_num}.'
            })
    else:
        # Placeholder inspection region when raw bits are not retained
        inspect_len = min(64, size)
        ranges.append({
            'start': base_offset,
            'end': base_offset + inspect_len - 1,
            'local_start': 0,
            'local_end': inspect_len - 1,
            'length': inspect_len,
            'window': window_num,
            'type': 'Flagged inspection region',
            'reason': f'Primary {inspect_len}-bit inspection slice from affected window {window_num}.'
        })
        
    return ranges

def get_short_explanation(row, inc=None, baseline=None, calibration=None):
    """
    Returns concise 3-field explanation:
    - Type: Bit bias, correlation, periodicity, repetition, burst, entropy drop, or mixed
    - Evidence: one short sentence
    - Measurement: one short sentence explaining how it was detected
    """
    if not row or row.get('state') in ['Healthy', 'Calibrating']:
        return {
            'type': 'Nominal',
            'evidence': 'This window conforms to expected baseline randomness.',
            'measurement': 'Comparing window statistical metrics with the calibrated baseline.'
        }
    
    # Determine dominant type
    sig_type = (inc.get('type') if inc else None)
    if not sig_type or sig_type == 'Unknown / unclassified':
        sigs = row.get('signatures', {})
        candidates = {k: v for k, v in sigs.items() if k not in ['Unknown / unclassified', 'Mixed failure']}
        if candidates and max(candidates.values()) > 20:
            sig_type = max(candidates, key=candidates.get)
        else:
            sig_type = 'Bit bias'
            
    b_mean = (baseline.get('mean', {}) if baseline else {}).get('bias', 0.0)
    obs_bias = row.get('bias', 0.0)
    shannon = row.get('shannon', 1.0)
    corr = row.get('autocorrelation')
    streak = row.get('longest_streak', 0)
    
    sig_lower = sig_type.lower()
    if 'bias' in sig_lower:
        direction = "more 1s" if obs_bias > b_mean else "more 0s"
        return {
            'type': 'Bit bias',
            'evidence': f"This window contains {direction} than the healthy baseline.",
            'measurement': "Comparing the 1-bit ratio with the calibrated baseline."
        }
    elif 'correlation' in sig_lower:
        return {
            'type': 'Correlation',
            'evidence': f"Adjacent bits show serial dependence (autocorrelation: {corr:+.4f} vs 0)." if corr is not None else "Adjacent bits show unexpected serial dependence.",
            'measurement': "Comparing each bit with the previous bit at lag 1."
        }
    elif 'periodic' in sig_lower:
        return {
            'type': 'Periodicity',
            'evidence': "Discrete Fourier Transform shows frequency components stronger than expected.",
            'measurement': "Measuring spectral concentration using DFT peak magnitude."
        }
    elif 'burst' in sig_lower:
        return {
            'type': 'Burst',
            'evidence': f"A localized streak of {streak} identical bits exceeds expected run lengths.",
            'measurement': "Detecting continuous identical bit streaks within the window."
        }
    elif 'repetition' in sig_lower:
        return {
            'type': 'Repetition',
            'evidence': "Repeated 32-bit block patterns appear consecutively in this window.",
            'measurement': "Comparing adjacent 32-bit blocks for identical sequences."
        }
    elif 'collapse' in sig_lower or 'entropy' in sig_lower:
        return {
            'type': 'Entropy drop',
            'evidence': f"Observed Shannon entropy ({shannon:.3f} bits/bit) falls below nominal boundary.",
            'measurement': "Comparing Shannon and min-entropy with the calibrated reference."
        }
    elif 'mixed' in sig_lower:
        return {
            'type': 'Mixed',
            'evidence': "Two or more independent statistical measurements exhibit concurrent anomalies.",
            'measurement': "Tracking simultaneous deviations across bias, dependence, and NIST tests."
        }
    elif 'drift' in sig_lower:
        return {
            'type': 'Gradual drift',
            'evidence': "Statistical indicators exhibit a persistent downward trend across time.",
            'measurement': "Evaluating Theil–Sen slope over a 20-window sliding history."
        }
    else:
        return {
            'type': sig_type,
            'evidence': "Observed statistics deviate from calibrated nominal limits.",
            'measurement': "Evaluating standardized feature change against CUSUM decision boundary."
        }

def extract_inconsistencies(rows, events, baseline, calibration, session_id='', timestamp='', size=10000, all_bits=None):
    """
    Groups degraded/warning windows into unified, deduplicated inconsistency records.
    Distinguishes first detected window from unknown physical onset.
    """
    if not rows:
        return [], dict(
            total_events=0,
            unique_affected_windows=0,
            flagged_ranges_count=0,
            first_detected='None (Healthy stream)',
            most_common_type='None',
            highest_severity='Healthy'
        )
    
    # Identify non-healthy windows
    anomalous_indices = [
        i for i, r in enumerate(rows)
        if r.get('state') in ['Early Warning', 'Degraded', 'Critical']
    ]
    
    if not anomalous_indices:
        return [], dict(
            total_events=0,
            unique_affected_windows=0,
            flagged_ranges_count=0,
            first_detected='None (Healthy stream)',
            most_common_type='None',
            highest_severity='Healthy'
        )
    
    # Cluster contiguous or closely spaced anomalous windows into distinct events
    clusters = []
    current_cluster = [anomalous_indices[0]]
    for idx in anomalous_indices[1:]:
        # If separated by at most 1 healthy window during transient fluctuation, keep in cluster
        if idx - current_cluster[-1] <= 2:
            current_cluster.append(idx)
        else:
            clusters.append(current_cluster)
            current_cluster = [idx]
    if current_cluster:
        clusters.append(current_cluster)
        
    inconsistencies = []
    severity_order = {'Early Warning': 1, 'Degraded': 2, 'Critical': 3}
    
    for c_idx, cluster in enumerate(clusters):
        cluster_rows = [rows[i] for i in cluster]
        first_row = cluster_rows[0]
        last_row = cluster_rows[-1]
        
        first_win = first_row['window']
        affected_windows = [r['window'] for r in cluster_rows]
        
        # Determine highest severity
        highest_state = max(cluster_rows, key=lambda r: severity_order.get(r.get('state', 'Early Warning'), 1)).get('state', 'Early Warning')
        
        # Determine dominant signature type across affected windows
        sig_totals = {}
        for r in cluster_rows:
            sigs = r.get('signatures', {})
            for k, v in sigs.items():
                if k not in ['Unknown / unclassified', 'Mixed failure']:
                    sig_totals[k] = sig_totals.get(k, 0) + v
        
        if sig_totals and max(sig_totals.values()) > 20:
            dominant_sig = max(sig_totals, key=sig_totals.get)
            # Check if second highest is also strong (> 60% of top) for mixed failure
            sorted_sigs = sorted(sig_totals.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_sigs) > 1 and sorted_sigs[1][1] >= 0.7 * sorted_sigs[0][1] and sorted_sigs[1][1] > 30 * len(cluster_rows):
                dominant_type = 'Mixed failure'
            else:
                dominant_type = dominant_sig
        else:
            dominant_type = 'Unknown / unclassified'
            
        meas_info = get_measurement_info(dominant_type)
        
        # Calculate bit ranges
        bit_start = (first_win - 1) * size
        bit_end = cluster_rows[-1]['window'] * size - 1
        affected_bits = len(affected_windows) * size
        
        # Extract localized flagged ranges for each window in the cluster
        flagged_ranges = []
        for r in cluster_rows:
            w_num = r['window']
            w_bits = None
            if all_bits is not None:
                w_start = (w_num - 1) * size
                w_end = min(len(all_bits), w_start + size)
                if w_end > w_start:
                    w_bits = all_bits[w_start:w_end]
            ranges = find_localized_ranges(r, w_bits, size)
            flagged_ranges.extend(ranges)
            
        # Baseline values
        base_means = baseline.get('mean', {})
        base_stds = baseline.get('std', {})
        
        # Observed values (mean & peak in cluster)
        obs_bias = float(np.mean([r.get('bias', 0.0) for r in cluster_rows]))
        obs_shannon = float(np.mean([r.get('shannon', 1.0) for r in cluster_rows]))
        obs_min_ent = float(np.mean([r.get('min_entropy', 1.0) for r in cluster_rows]))
        obs_corrs = [r.get('autocorrelation') for r in cluster_rows if r.get('autocorrelation') is not None]
        obs_corr = float(np.mean(obs_corrs)) if obs_corrs else None
        obs_spectral = [r.get('spectral') for r in cluster_rows if r.get('spectral') is not None]
        obs_spec = float(np.mean(obs_spectral)) if obs_spectral else None
        
        # Differences from baseline
        diff_bias = obs_bias - base_means.get('bias', 0.0)
        max_z = 0.0
        for r in cluster_rows:
            z_vals = [abs(zv) for zv in r.get('z', []) if zv is not None]
            if z_vals:
                max_z = max(max_z, max(z_vals))
                
        # Applicable NIST tests across cluster
        nist_failures = []
        for r in cluster_rows:
            for t in r.get('tests', []):
                if t.get('status') == 'FAIL':
                    if t['name'] not in [nf['name'] for nf in nist_failures]:
                        nist_failures.append({
                            'name': t['name'],
                            'p_value': t.get('p_value'),
                            'status': t['status'],
                            'interpretation': t.get('interpretation', ''),
                            'first_failed_window': r['window']
                        })
                        
        # CUSUM info
        max_cusum = max(r.get('change_score', 0.0) for r in cluster_rows)
        cusum_thresh = float(calibration.get('threshold', 0.0))
        
        # Evidence strength
        if highest_state == 'Critical' or max_z >= 10.0 or len(nist_failures) >= 3:
            strength = f'Critical (Peak |z|={max_z:.1f}, {len(nist_failures)} NIST failures, CUSUM={max_cusum:.2f})'
        elif highest_state == 'Degraded' or max_z >= 5.0 or len(nist_failures) >= 1:
            strength = f'Strong (Peak |z|={max_z:.1f}, {len(nist_failures)} NIST failures, CUSUM={max_cusum:.2f})'
        else:
            strength = f'Moderate (Peak |z|={max_z:.1f}, CUSUM={max_cusum:.2f}/{cusum_thresh:.2f})'
            
        # Status
        status = 'Recovered' if cluster[-1] < len(rows) - 1 and rows[-1].get('state') == 'Healthy' else 'Active'
        
        # Evidence explanation
        corr_str = 'N/A' if obs_corr is None else f'{obs_corr:+.4f}'
        explanation = (
            f"Window {first_win} was the first window with persistent evidence. "
            f"The affected range covers {len(affected_windows)} window(s) (bit offset {bit_start:,} to {bit_end:,}). "
            f"Observed marginal Shannon entropy is {obs_shannon:.5f} bits/bit, signed bias is {obs_bias:+.4f} (baseline {base_means.get('bias', 0.0):+.4f}), "
            f"and lag-1 serial correlation is {corr_str}. "
            f"{len(nist_failures)} NIST test families exhibited statistical failures in this interval. "
            f"CUSUM change statistic reached {max_cusum:.3f} against calibrated threshold {cusum_thresh:.3f}. "
            f"{meas_info['disclaimer']}"
        )
        
        inc_id = f"INC-{c_idx+1:03d}"
        
        record = {
            'id': inc_id,
            'type': dominant_type,
            'severity': highest_state,
            'first_detected_window': first_win,
            'last_affected_window': cluster_rows[-1]['window'],
            'affected_windows': affected_windows,
            'affected_windows_count': len(affected_windows),
            'bit_start': bit_start,
            'bit_end': bit_end,
            'affected_bits': affected_bits,
            'flagged_ranges': flagged_ranges,
            'flagged_ranges_count': len(flagged_ranges),
            'session_id': session_id,
            'timestamp': timestamp,
            'baseline_values': {
                'bias': base_means.get('bias', 0.0),
                'autocorrelation': base_means.get('autocorrelation', 0.0),
                'spectral': base_means.get('spectral', 0.0),
                'block_entropy': base_means.get('block_entropy', 0.0),
                'shannon': 1.0,
                'min_entropy': 1.0
            },
            'observed_values': {
                'bias': obs_bias,
                'autocorrelation': obs_corr,
                'spectral': obs_spec,
                'shannon': obs_shannon,
                'min_entropy': obs_min_ent,
                'max_streak': max(r.get('longest_streak', 0) for r in cluster_rows)
            },
            'diff_from_baseline': {
                'bias_delta': diff_bias,
                'peak_z_score': max_z
            },
            'nist_tests': nist_failures,
            'cusum_contribution': {
                'max_score': max_cusum,
                'threshold': cusum_thresh,
                'exceeded': max_cusum >= cusum_thresh
            },
            'evidence_strength': strength,
            'evidence_explanation': explanation,
            'measurement_explanation': meas_info,
            'recommended_check': meas_info['recommended_check'],
            'status': status,
            'physical_onset_note': (
                f"First detected window: Window {first_win} (earliest point where statistical evidence met detection criteria). "
                f"Physical onset: Unknown without external hardware telemetry."
            )
        }
        
        inconsistencies.append(record)
        
    # Calculate summary
    unique_windows = len(set(w for inc in inconsistencies for w in inc['affected_windows']))
    total_flagged_ranges = sum(inc['flagged_ranges_count'] for inc in inconsistencies)
    first_detected_str = f"Window {inconsistencies[0]['first_detected_window']} ({inconsistencies[0]['id']})" if inconsistencies else 'None'
    
    # Most common type
    type_counts = {}
    for inc in inconsistencies:
        type_counts[inc['type']] = type_counts.get(inc['type'], 0) + 1
    most_common = max(type_counts, key=type_counts.get) if type_counts else 'None'
    
    # Highest severity
    severities = [inc['severity'] for inc in inconsistencies]
    if 'Critical' in severities:
        highest_sev = 'Critical'
    elif 'Degraded' in severities:
        highest_sev = 'Degraded'
    elif 'Early Warning' in severities:
        highest_sev = 'Early Warning'
    else:
        highest_sev = 'Healthy'
        
    summary_obj = {
        'total_events': len(inconsistencies),
        'unique_affected_windows': unique_windows,
        'flagged_ranges_count': total_flagged_ranges,
        'first_detected': first_detected_str,
        'most_common_type': most_common,
        'highest_severity': highest_sev
    }
    
    return inconsistencies, summary_obj
