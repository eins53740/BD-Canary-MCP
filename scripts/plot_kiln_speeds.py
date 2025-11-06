import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict

# Data from read_timeseries tool
data: List[Dict[str, str]] = [
    {"timestamp": "2025-11-05T15:59:28.8130000+00:00", "value": "2.407"},
    {"timestamp": "2025-11-05T20:58:28.8040000+00:00", "value": "2.509"},
    {"timestamp": "2025-11-05T21:59:28.8080000+00:00", "value": "2.508"}
]

# Convert timestamps to datetime objects
timestamps = [datetime.fromisoformat(d['timestamp']) for d in data]
values = [float(d['value']) for d in data]

# Plotting the data
plt.figure(figsize=(14, 7))
plt.plot(timestamps, values, label='Kiln Shell Speed', marker='o')
plt.title('Kiln Shell Speed Over Last 8 Hours')
plt.xlabel('Timestamp')
plt.ylabel('Speed (units)')
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()

# Save the plot
plt.savefig('kiln_shell_speed_plot.png')

# Show the plot
plt.show()
