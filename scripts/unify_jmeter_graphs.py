import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

jtl = sys.argv[1]
out_dir = sys.argv[2]

df = pd.read_csv(jtl)
# normalize column names to lowercase for robustness
df.columns = [c.lower() for c in df.columns]

os.makedirs(out_dir, exist_ok=True)

# Response Time
plt.figure()
if 'elapsed' in df.columns:
	df['elapsed'].plot()
else:
	# fallback to first numeric column
	numeric_cols = df.select_dtypes(include=['number']).columns
	if len(numeric_cols) > 0:
		df[numeric_cols[0]].plot()
	else:
		raise RuntimeError('No numeric column found for response time')
plt.title("Response Time (ms)")
plt.ylabel("ms")
plt.xlabel("samples")
plt.savefig(f"{out_dir}/response_time.png")

# Throughput
plt.figure()
ts_col = 'timestamp' if 'timestamp' in df.columns else ('timestamp' if 'timestamp' in df.columns else None)
if ts_col is None and 'timeStamp' in df.columns:
	ts_col = 'timestamp'
if ts_col and ts_col in df.columns:
	try:
		df['timeindex'] = pd.to_datetime(df[ts_col], unit='ms')
		df.set_index('timeindex', inplace=True)
	except Exception:
		# try parsing as standard datetime
		df['timeindex'] = pd.to_datetime(df[ts_col], errors='coerce')
		df.set_index('timeindex', inplace=True)
else:
	# no timestamp column; create simple index
	df.index = range(len(df))
df['throughput'] = 1
try:
	df['throughput'].resample("1s").sum().plot()
except Exception:
	# fallback: plot rolling sum over 50 samples
	df['throughput'].rolling(window=min(50, len(df))).sum().plot()
plt.title("Throughput (req/s)")
plt.ylabel("req/s")
plt.savefig(f"{out_dir}/throughput.png")

# Error rate
plt.figure()
if 'success' in df.columns:
	error_rate = (df['success'] == False).rolling(50).mean()
else:
	# try to infer errors from response code if present
	if 'responsecode' in df.columns:
		error_rate = (df['responsecode'].astype(str).str.startswith('2') == False).rolling(50).mean()
	else:
		error_rate = pd.Series([0]*len(df))
error_rate.plot()
plt.title("Error Rate (%)")
plt.savefig(f"{out_dir}/error_rate.png")

print("✅ Gráficos JMeter unificados gerados!")
