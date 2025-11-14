import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

jtl = sys.argv[1]
out_dir = sys.argv[2]

df = pd.read_csv(jtl)

os.makedirs(out_dir, exist_ok=True)

# Response Time
plt.figure()
df['elapsed'].plot()
plt.title("Response Time (ms)")
plt.ylabel("ms")
plt.xlabel("samples")
plt.savefig(f"{out_dir}/response_time.png")

# Throughput
plt.figure()
df['timeStamp'] = pd.to_datetime(df['timeStamp'], unit='ms')
df.set_index('timeStamp', inplace=True)
df['throughput'] = 1
df['throughput'].resample("1s").sum().plot()
plt.title("Throughput (req/s)")
plt.ylabel("req/s")
plt.savefig(f"{out_dir}/throughput.png")

# Error rate
plt.figure()
error_rate = (df['success'] == False).rolling(50).mean()
error_rate.plot()
plt.title("Error Rate (%)")
plt.savefig(f"{out_dir}/error_rate.png")

print("✅ Gráficos JMeter unificados gerados!")
