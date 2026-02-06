# 📊 Data Science & ML Theory Used in Smart Parking Platform

## 1. Computer Vision (CV)

### 1.1 Object Detection — YOLOv8 (You Only Look Once)
- **Theory:** Single-shot detector that frames object detection as a regression problem. The image is divided into an S×S grid; each cell predicts B bounding boxes with confidence scores and C class probabilities simultaneously.
- **Loss Function:** Composite loss = λ_coord · Σ(localization loss) + Σ(confidence loss) + λ_class · Σ(classification loss)
- **Used For:** Detecting vehicles (car, truck, motorcycle, bus) in parking zone camera feeds.
- **Key Concepts:** Anchor-free detection, multi-scale feature fusion (PANet), CSPDarknet backbone.

### 1.2 Image Preprocessing Pipeline
- **Gaussian Blur:** Kernel-based smoothing to reduce noise — G(x,y) = (1/2πσ²) · e^(-(x²+y²)/2σ²)
- **Canny Edge Detection:** Multi-stage edge detector (gradient computation → non-maximum suppression → hysteresis thresholding)
- **Perspective Transform (Homography):** Maps bird's-eye view of parking lot using 3×3 transformation matrix H where x' = Hx
- **Morphological Operations:** Dilation/erosion for license plate region cleanup
- **Used For:** Preprocessing frames before vehicle detection and license plate extraction.

### 1.3 License Plate Recognition (ALPR/ANPR)
- **Character Segmentation:** Connected component analysis + contour detection
- **OCR Engine:** Tesseract LSTM-based recognizer — uses a recurrent neural network with CTC (Connectionist Temporal Classification) loss
- **CTC Loss:** Enables sequence prediction without requiring pre-segmented characters — L_CTC = -ln(Σ_π∈B⁻¹(y) Π_t p(π_t|x))
- **Preprocessing:** Adaptive thresholding (Otsu's method), skew correction via Hough transform

## 2. Deep Learning

### 2.1 Convolutional Neural Networks (CNNs)
- **Theory:** Hierarchical feature extraction through learnable convolutional filters
- **Layers Used:** Conv2D → BatchNorm → ReLU → MaxPool → Dropout → Dense
- **Backpropagation:** Gradient computation via chain rule for weight updates
- **Used For:** Feature extraction backbone in vehicle detection model

### 2.2 Transfer Learning
- **Theory:** Leveraging pre-trained weights (COCO dataset) and fine-tuning on parking-specific data
- **Approach:** Freeze early layers (generic features), fine-tune later layers (domain-specific features)
- **Used For:** YOLOv8 model adapted for parking lot vehicle detection with limited training data

### 2.3 Batch Normalization
- **Theory:** Normalizes layer inputs — x̂ = (x - μ_B) / √(σ²_B + ε), then scales/shifts: y = γx̂ + β
- **Benefit:** Faster convergence, acts as regularizer, enables higher learning rates

## 3. Time Series Analysis & Forecasting

### 3.1 Occupancy Prediction — ARIMA/SARIMA
- **Theory:** AutoRegressive Integrated Moving Average captures temporal patterns
- **SARIMA(p,d,q)(P,D,Q,s):** Handles both trend and seasonality in parking occupancy
- **Used For:** Predicting parking demand for next 1-24 hours per zone

### 3.2 Exponential Smoothing (Holt-Winters)
- **Theory:** Weighted average with exponentially decreasing weights for older observations
- **Triple Exponential:** Captures level (α), trend (β), and seasonality (γ)
- **Used For:** Smoothing real-time occupancy counts, short-term availability prediction

### 3.3 Moving Averages
- **Simple Moving Average (SMA):** Equal-weight window average for trend identification
- **Exponential Moving Average (EMA):** Recent-biased smoothing for real-time dashboards
- **Used For:** Dashboard trend lines, anomaly baseline computation

## 4. Statistical Methods

### 4.1 Hypothesis Testing
- **Chi-Square Test:** Testing independence between zone location and peak utilization times
- **t-Test:** Comparing mean occupancy between weekdays vs weekends
- **ANOVA:** Comparing utilization across multiple zones simultaneously
- **Used For:** Analytics reports, identifying statistically significant patterns

### 4.2 Bayesian Inference
- **Theory:** P(A|B) = P(B|A) · P(A) / P(B) — updating beliefs with new evidence
- **Used For:** Updating parking availability probability as new sensor data arrives; confidence calibration for license plate recognition

### 4.3 Kernel Density Estimation (KDE)
- **Theory:** Non-parametric density estimation — f̂(x) = (1/nh) Σ K((x-xᵢ)/h)
- **Used For:** Generating heatmaps of parking utilization density across zones

### 4.4 Poisson Process
- **Theory:** Models random arrival events — P(N(t)=k) = (λt)^k · e^(-λt) / k!
- **Used For:** Modeling vehicle arrival rates, queue length estimation

## 5. Graph Theory (Neo4j)

### 5.1 Shortest Path (Dijkstra's Algorithm)
- **Theory:** Greedy algorithm finding minimum-weight path between nodes
- **Complexity:** O((V + E) log V) with priority queue
- **Used For:** Routing vehicles to nearest available parking zone

### 5.2 Community Detection (Louvain Algorithm)
- **Theory:** Modularity optimization — Q = (1/2m) Σ [Aᵢⱼ - kᵢkⱼ/2m] δ(cᵢ,cⱼ)
- **Used For:** Grouping related parking zones for coordinated management

### 5.3 Centrality Measures
- **Betweenness Centrality:** Identifies critical junction zones
- **PageRank:** Ranks zones by traffic flow importance
- **Used For:** Infrastructure planning, identifying bottleneck zones

## 6. Anomaly Detection

### 6.1 Z-Score Method
- **Theory:** Flags observations where |z| = |(x - μ)/σ| > threshold (typically 3)
- **Used For:** Detecting unusual occupancy spikes or drops

### 6.2 Isolation Forest
- **Theory:** Anomalies are isolated in fewer random partitions — anomaly score s(x,n) based on average path length
- **Used For:** Detecting unusual parking patterns, potential security events

## 7. Optimization

### 7.1 Linear Programming
- **Theory:** Maximize/minimize objective function subject to linear constraints
- **Used For:** Optimal space allocation across zones given demand forecasts

### 7.2 Queueing Theory (M/M/c Queue)
- **Theory:** Models multi-server queues — traffic intensity ρ = λ/(cμ)
- **Used For:** Estimating wait times at parking entries, capacity planning

## 8. Data Engineering Concepts

### 8.1 ETL Pipeline Design
- **Extract:** Camera feeds, IoT sensors, manual entry
- **Transform:** Frame sampling, image augmentation, feature engineering
- **Load:** Time-series DB for events, graph DB for relationships, blob storage for frames

### 8.2 Stream Processing
- **Theory:** Real-time event processing with windowed aggregations
- **Tumbling Windows:** Fixed non-overlapping intervals for batch counting
- **Sliding Windows:** Overlapping intervals for moving average computation

### 8.3 Data Warehousing (Star Schema)
- **Fact Table:** parking_events (timestamp, zone_id, vehicle_count, occupancy_rate)
- **Dimensions:** dim_zone, dim_time, dim_vehicle_type, dim_camera
- **Used For:** Azure Synapse analytics queries, historical trend analysis

## 9. Authentication & Security Theory

### 9.1 JWT (JSON Web Tokens)
- **Theory:** Stateless authentication — Header.Payload.Signature (HMAC-SHA256)
- **RBAC:** Role claims embedded in token payload for access control

### 9.2 Password Security
- **bcrypt:** Adaptive hash function with configurable work factor — resistant to brute force
- **Salt:** Random per-user salt prevents rainbow table attacks
