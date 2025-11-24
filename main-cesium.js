import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

// IMPORTANT: Paste your Cesium Ion access token here.
// 1. Go to https://cesium.com/ion/signup and create a free account.
// 2. Go to the "Access Tokens" tab.
// 3. Copy the "Default" token and paste it below.
Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI1ZjE0YmM0MS03MDdkLTQyZmMtODFiMC00YjljZDcyMzdhYTEiLCJpZCI6MzYxNzI0LCJpYXQiOjE3NjM1Mzg0NTF9.gndeuPVI38HHOj7CgWhS5lCij_BwzL6SmSPkubXvP_4';

// Power plant locations in Karnataka area
// TO CHANGE POSITIONS: Update the 'lat' (latitude) and 'lon' (longitude) values below.
const bengaluruPlants = [
  { name: 'Tuppadahalli Wind Power Station', type: 'wind', capacity: '56 MW', lat: 13.94903334908406, lon: 76.0486864696537 },
  { name: 'Kaiga Nuclear Power Plant', type: 'nuclear', capacity: '880 MW', lat: 14.865460, lon: 74.439071 },
  { name: 'Pavagada Solar Park', type: 'solar', capacity: '2050 MW', lat: 14.139977, lon: 77.314803 },
  { name: 'Shivanasamudra Hydro Plant', type: 'hydro', capacity: '42 MW', lat: 12.298628, lon: 77.170727 },
  { name: 'Mahatma Gandhi Hydro Plant', type: 'hydro', capacity: '139 MW', lat: 14.227473, lon: 74.799363 },
  { name: 'Almatti Dam', type: 'hydro', capacity: '290 MW', lat: 16.331017, lon: 75.887133 },
  { name: 'Jindal Jogihalli Wind Plant', type: 'wind', capacity: '20 MW', lat: 14.671766, lon: 76.421704 },
  { name: 'Raichur Solar Park', type: 'solar', capacity: '100 MW', lat: 16.134622, lon: 77.125315 }
];

// Initialize Cesium Viewer with 3D terrain (Requires valid Token)
const viewer = new Cesium.Viewer('cesiumContainer', {
  terrain: Cesium.Terrain.fromWorldTerrain({
    requestWaterMask: true,
    requestVertexNormals: true
  }),
  animation: true,       // Enable animation control
  timeline: true,        // Enable timeline
  baseLayerPicker: false,
  geocoder: false,
  homeButton: true,
  sceneModePicker: true,
  navigationHelpButton: false,
  selectionIndicator: true,
  infoBox: false,
  fullscreenButton: true,
  vrButton: false,
  shouldAnimate: true    // Start animation by default
});

// Configure Clock for 24h simulation
const start = Cesium.JulianDate.fromDate(new Date(2023, 6, 1, 0)); // Start at midnight
const stop = Cesium.JulianDate.addDays(start, 1, new Cesium.JulianDate());
viewer.clock.startTime = start.clone();
viewer.clock.stopTime = stop.clone();
viewer.clock.currentTime = start.clone();
viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP; // Loop the day
viewer.clock.multiplier = 3600; // 1 second real time = 1 hour simulation time
viewer.timeline.zoomTo(start, stop);

// Add Cesium OSM Buildings for 3D cities
try {
  const buildingsTileset = await Cesium.createOsmBuildingsAsync();
  viewer.scene.primitives.add(buildingsTileset);
} catch (error) {
  console.error('Error loading 3D buildings:', error);
}

// Enable lighting for better 3D effect
viewer.scene.globe.enableLighting = true;
viewer.shadows = true; // Enable shadows for sun rotation effect

// Color scheme for plant types
const plantColors = {
  hydro: Cesium.Color.DEEPSKYBLUE,
  nuclear: Cesium.Color.ORANGE,
  solar: Cesium.Color.YELLOW,
  wind: Cesium.Color.CYAN
};

// Paths to the 3D models (GLB format required for Cesium)
const plantModels = {
  hydro: 'models/energy-plants/gravity-dam/USACE-3D-22-002-dam_converted.glb',
  nuclear: 'models/energy-plants/nuclear-power-plant/ImageToStl.com_aes/aes_converted.glb',
  solar: 'models/energy-plants/Solar_Panels_V1_L3.123cc8f890de-f0dc-4416-91ba-2d06cafb9a74/Solar_Panels_V1_L3.123cc8f890de-f0dc-4416-91ba-2d06cafb9a74/10781_Solar-Panels_V1_converted.glb',
  wind: 'models/energy-plants/38-eolic-obj/EolicOBJ_converted.glb'
};

// Simulation State (Global)
const gridState = {
  totalDemand: 0,
  totalGen: 0,
  renewablePct: 0,
  frequency: 50.0,
  marketPrice: 0,      // $/MWh
  carbonIntensity: 0,  // gCO2/kWh
  totalRevenue: 0      // Cumulative $
};

const plantRealtimeData = new Map(); // Store real-time data for each plant
let selectedPlantName = null; // Track currently selected plant

// Add plant entities to the viewer
bengaluruPlants.forEach(plant => {
  // Fix for levitating solar panels:
  // If it's a solar plant, we might need to lower it slightly or clamp it differently.
  // Using RELATIVE_TO_GROUND allows us to set a height (altitude).
  // A negative height will bury it, a positive will lift it.
  // Adjust 'heightOffset' as needed for your specific model.
  let heightOffset = 0;
  if (plant.type === 'solar') {
    heightOffset = -2500; // Drastically increased offset to fix levitation
  }

  const position = Cesium.Cartesian3.fromDegrees(plant.lon, plant.lat, heightOffset);
  const color = plantColors[plant.type] || Cesium.Color.WHITE;

  viewer.entities.add({
    name: `${plant.name} (${plant.capacity})`,
    position: position,
    description: `
      <h2>${plant.name}</h2>
      <p><strong>Type:</strong> ${plant.type.charAt(0).toUpperCase() + plant.type.slice(1)}</p>
      <p><strong>Capacity:</strong> ${plant.capacity}</p>
    `,
    model: {
      uri: plantModels[plant.type],
      // TO CHANGE SIZE: Adjust the 'scale' value below.
      scale: 20.0,

      // --- COMMENT OUT THESE 3 LINES TO RESTORE ORIGINAL COLORS ---
      // color: color, // Tint the model with the plant type color
      // colorBlendMode: Cesium.ColorBlendMode.HIGHLIGHT,
      // colorBlendAmount: 0.5,
      // ------------------------------------------------------------

      heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
    }
  });
});

// Draw power lines (connections) between plants to simulate a grid
let powerGridEntity;
function drawPowerLines() {
  // TO CHANGE POWER LINES: Modify how 'positions' are calculated here.
  // Currently it connects plants in the order they appear in the list.
  // Create a sequence of positions connecting the plants
  // We'll connect them in the order they appear in the list, and close the loop
  const positions = bengaluruPlants.map(plant => Cesium.Cartesian3.fromDegrees(plant.lon, plant.lat));

  // Close the loop by adding the first point at the end
  if (positions.length > 0) {
    positions.push(positions[0]);
  }

  powerGridEntity = viewer.entities.add({
    name: 'Power Grid Connections',
    polyline: {
      positions: positions,
      width: 3,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: new Cesium.CallbackProperty(() => {
          // Pulse glow based on total generation (0.1 to 0.5)
          const loadFactor = Math.min(1.0, (gridState.totalGen || 0) / 1500);
          return 0.1 + (loadFactor * 0.4);
        }, false),
        taperPower: 0.5,
        color: new Cesium.CallbackProperty(() => {
          // Red if unstable frequency, Cyan if stable
          if (gridState.frequency < 49.8 || gridState.frequency > 50.2) {
            return Cesium.Color.ORANGERED;
          }
          return Cesium.Color.CYAN;
        }, false),
      }),
      clampToGround: true // Follow the terrain
    }
  });
}

drawPowerLines();

// Fly the camera to Bengaluru
viewer.camera.flyTo({
  destination: Cesium.Cartesian3.fromDegrees(77.5946, 12.9716, 50000), // Bengaluru, 50km altitude
  orientation: {
    heading: Cesium.Math.toRadians(0),
    pitch: Cesium.Math.toRadians(-45),
    roll: 0
  },
  duration: 2 // seconds
});

// --- UI Functions ---

// Function to build the plant list in the UI
function buildPlantListUI() {
  const plantList = document.getElementById('plantList');
  plantList.innerHTML = ''; // Clear existing list

  const categories = {
    hydro: [],
    nuclear: [],
    solar: [],
    wind: []
  };

  // Group plants by type
  bengaluruPlants.forEach(plant => {
    categories[plant.type].push(plant);
  });

  // Create list items for each category
  for (const category in categories) {
    if (categories[category].length === 0) continue;

    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'plant-category';

    const categoryTitle = document.createElement('div');
    categoryTitle.className = 'category-title';
    categoryTitle.textContent = `${category.charAt(0).toUpperCase() + category.slice(1)} Power`;
    categoryDiv.appendChild(categoryTitle);

    categories[category].forEach(plant => {
      const item = document.createElement('div');
      item.className = 'plant-item';

      const nameDiv = document.createElement('div');
      nameDiv.className = 'plant-name';
      nameDiv.textContent = plant.name;
      item.appendChild(nameDiv);

      const infoDiv = document.createElement('div');
      infoDiv.className = 'plant-info';

      const capacitySpan = document.createElement('span');
      capacitySpan.className = 'plant-capacity';
      capacitySpan.textContent = plant.capacity;
      infoDiv.appendChild(capacitySpan);

      item.appendChild(infoDiv);

      item.onclick = () => {
        const entity = viewer.entities.values.find(e => e.name === `${plant.name} (${plant.capacity})`);
        if (entity) {
          viewer.selectedEntity = entity; // Select the entity
          showPlantDetail(plant.name); // Show custom dashboard
          viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(plant.lon, plant.lat, 5000), // Fly closer
            orientation: {
              heading: Cesium.Math.toRadians(0),
              pitch: Cesium.Math.toRadians(-35),
              roll: 0
            },
            duration: 1.5
          });
        }
      };
      categoryDiv.appendChild(item);
    });
    plantList.appendChild(categoryDiv);
  }
}

// Initial call to build the UI
buildPlantListUI();

// Listen for entity selection on the map (e.g. clicking a 3D model)
viewer.selectedEntityChanged.addEventListener((entity) => {
  if (entity && entity.name) {
    // Extract plant name from entity name "Name (Capacity)"
    const nameMatch = entity.name.match(/^(.*?) \(/);
    if (nameMatch) {
      showPlantDetail(nameMatch[1]);
    }
  } else {
    // If deselected (clicking empty space), hide panel
    // Optional: decide if we want to auto-hide or keep it open
    // hidePlantDetail(); 
  }
});

// --- Draggable UI Logic ---
function makeElementDraggable(elementId, handleId) {
  const element = document.getElementById(elementId);
  const handle = document.querySelector(handleId);

  if (!element || !handle) return;

  let isDragging = false;
  let startX, startY, initialLeft, initialTop;

  handle.style.cursor = 'grab';

  handle.addEventListener('mousedown', (e) => {
    // Allow interaction with buttons inside the handle
    if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
      return;
    }

    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;

    // Get current position (computed style handles both 'left/top' and 'transform' if needed, 
    // but here we are using absolute positioning with right/top initially. 
    // We need to switch to left/top for dragging to work smoothly from any position)
    const rect = element.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;

    // Switch from 'right' positioning to 'left' to allow free movement
    element.style.right = 'auto';
    element.style.left = `${initialLeft}px`;
    element.style.top = `${initialTop}px`;
    element.style.bottom = 'auto';

    // IMPORTANT: Remove the transform (translate -50%, -50%) because we are now positioning absolutely
    // based on the calculated rect. If we don't remove this, it will jump up/left.
    element.style.transform = 'none';

    handle.style.cursor = 'grabbing';

    // Prevent text selection during drag
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    element.style.left = `${initialLeft + dx}px`;
    element.style.top = `${initialTop + dy}px`;
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      handle.style.cursor = 'grab';
    }
  });
}

// Initialize draggable card
makeElementDraggable('plantCard', '.card-header');
makeElementDraggable('gridMonitor', '.monitor-header'); // Make monitor draggable too
makeElementDraggable('plantDetailPanel', '.panel-header'); // Make detail panel draggable

// --- Plant Detail Panel Logic ---

function showPlantDetail(plantName) {
  selectedPlantName = plantName;
  const panel = document.getElementById('plantDetailPanel');
  panel.classList.add('visible');
  updatePlantDetailPanel(plantName);
}

function hidePlantDetail() {
  selectedPlantName = null;
  document.getElementById('plantDetailPanel').classList.remove('visible');
  viewer.selectedEntity = undefined; // Deselect entity
}

function updatePlantDetailPanel(plantName) {
  const data = plantRealtimeData.get(plantName);
  if (!data) return;

  document.getElementById('detailName').textContent = plantName;
  document.getElementById('detailType').textContent = data.type.toUpperCase();

  const statusElem = document.getElementById('detailStatus');
  statusElem.textContent = data.status;
  statusElem.style.color = data.status === 'ONLINE' ? '#4caf50' : '#ffb74d';
  statusElem.style.background = data.status === 'ONLINE' ? 'rgba(76, 175, 80, 0.2)' : 'rgba(255, 183, 77, 0.2)';

  document.getElementById('detailOutput').textContent = data.output.toFixed(1);

  const pct = Math.min(100, (data.output / data.maxCapacity) * 100);
  document.getElementById('detailOutputBar').style.width = `${pct}%`;

  document.getElementById('detailEfficiency').textContent = `${data.efficiency.toFixed(1)}%`;
  document.getElementById('detailTemp').textContent = `${data.temperature.toFixed(1)}°C`;
}

// Close button handler
const closeBtn = document.getElementById('closeDetail');
closeBtn.addEventListener('click', hidePlantDetail);
// Prevent drag start when clicking close button
closeBtn.addEventListener('mousedown', (e) => {
  e.stopPropagation();
});

// --- Real-time Simulation Logic ---

// Helper to parse capacity string "45 MW" -> 45
function parseCapacity(capStr) {
  return parseFloat(capStr.split(' ')[0]);
}

// Update Simulation Loop (runs every frame)
viewer.clock.onTick.addEventListener((clock) => {
  const time = Cesium.JulianDate.toGregorianDate(clock.currentTime);
  const hour = time.hour + time.minute / 60; // 0.0 to 24.0

  // 1. Calculate Demand Curve (Advanced Model)
  // Base load + Morning/Evening Peaks + Industrial Noise
  const baseLoad = 600;
  const morningPeak = 350 * Math.exp(-Math.pow(hour - 9.5, 2) / 3); // Peak at 9:30 AM
  const eveningPeak = 450 * Math.exp(-Math.pow(hour - 19.5, 2) / 4); // Peak at 7:30 PM
  const industrialNoise = (Math.sin(hour * 10) + Math.cos(hour * 23)) * 15; // High freq noise
  gridState.totalDemand = Math.round(baseLoad + morningPeak + eveningPeak + industrialNoise);

  // 2. Calculate Generation per Plant
  let currentTotalGen = 0;
  let currentRenewableGen = 0;
  let currentCarbonEmissions = 0; // kgCO2/h

  bengaluruPlants.forEach(plant => {
    const maxCap = parseCapacity(plant.capacity);
    let currentOutput = 0;
    let emissionFactor = 0; // kgCO2/MWh

    if (plant.type === 'solar') {
      // Solar: Bell curve from 6am to 6pm
      if (hour > 6 && hour < 18) {
        const sunIntensity = Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI));
        currentOutput = maxCap * sunIntensity;
        // Cloud cover simulation (Perlin-like noise)
        const cloudCover = Math.sin(hour * 5) * 0.1 + 0.9;
        currentOutput *= cloudCover;
      }
      emissionFactor = 0;
    } else if (plant.type === 'wind') {
      // Wind: Diurnal pattern + Gusts
      const windBase = 0.4 + 0.3 * Math.sin((hour - 14) / 24 * Math.PI * 2); // Higher in evening
      const gust = (Math.sin(hour * 45) * 0.2);
      currentOutput = maxCap * Math.max(0, windBase + gust);
      emissionFactor = 0;
    } else if (plant.type === 'hydro') {
      // Hydro: Dispatchable - ramps up to meet demand peaks
      const demandFactor = (gridState.totalDemand - 600) / 500; // Normalized peak demand
      currentOutput = maxCap * (0.4 + Math.max(0, demandFactor * 0.6));
      emissionFactor = 0;
    } else if (plant.type === 'nuclear') {
      // Nuclear: Base load, very stable
      currentOutput = maxCap * 0.98;
      emissionFactor = 12; // Very low but non-zero lifecycle
    }

    currentTotalGen += currentOutput;
    currentCarbonEmissions += currentOutput * emissionFactor;

    if (['solar', 'wind', 'hydro'].includes(plant.type)) {
      currentRenewableGen += currentOutput;
    }

    // Store real-time data for this plant
    plantRealtimeData.set(plant.name, {
      output: currentOutput,
      maxCapacity: maxCap,
      efficiency: (currentOutput / maxCap) * 100,
      temperature: 25 + (currentOutput / maxCap) * 40 + (Math.random() * 2), // Simulated temp
      status: currentOutput > 0.1 ? 'ONLINE' : 'STANDBY',
      type: plant.type
    });
  });

  // 3. Grid Physics & Economics

  // Import/Export Logic: If Demand > Gen, we import dirty power. If Gen > Demand, we export.
  const netLoad = gridState.totalDemand - currentTotalGen;

  if (netLoad > 0) {
    // Importing power (usually fossil fuel heavy peaker plants)
    currentTotalGen += netLoad; // Grid balances by importing
    currentCarbonEmissions += netLoad * 450; // Gas peaker ~450 kgCO2/MWh
  }

  // Frequency Simulation with Inertia
  const balance = (currentTotalGen - gridState.totalDemand); // Should be 0 if balanced perfectly
  // Add some "error" to simulation to make frequency wobble
  const controlError = (Math.random() - 0.5) * 5;
  const targetFreq = 50.0 + (controlError / 1000);
  // Smooth transition (Inertia)
  gridState.frequency = gridState.frequency * 0.95 + targetFreq * 0.05;

  // Economics
  // Price spikes when demand is high or renewables are low
  const scarcityFactor = Math.max(0, (gridState.totalDemand / 1200)); // 0 to 1+
  const basePrice = 40; // $/MWh
  gridState.marketPrice = basePrice + (scarcityFactor * scarcityFactor * 100);

  // Revenue Accumulation (Time step is roughly 1/60th of an hour in real time, but simulation is 3600x speed)
  // 1 real sec = 1 sim hour. 60fps. 
  // So each tick is 1/60th of a real second = 1/60th of a sim hour = 1 sim minute.
  const hoursPerTick = 1 / 60;
  const revenueTick = (gridState.totalDemand * gridState.marketPrice) * hoursPerTick;
  gridState.totalRevenue += revenueTick;

  // Metrics
  gridState.totalGen = Math.round(currentTotalGen);
  gridState.renewablePct = Math.round((currentRenewableGen / currentTotalGen) * 100) || 0;
  gridState.carbonIntensity = Math.round(currentCarbonEmissions / currentTotalGen); // gCO2/kWh approx

  // 4. Update Dashboard UI
  // updateDashboard(hour);

  // 5. Update Plant Detail Panel if open
  if (selectedPlantName) {
    updatePlantDetailPanel(selectedPlantName);
  }
});

function updateDashboard(hour) {
  // Clock
  const hh = Math.floor(hour).toString().padStart(2, '0');
  const mm = Math.floor((hour % 1) * 60).toString().padStart(2, '0');
  document.getElementById('clockDisplay').textContent = `${hh}:${mm}`;

  // Values
  document.getElementById('totalDemand').textContent = gridState.totalDemand.toLocaleString();
  document.getElementById('totalGen').textContent = gridState.totalGen.toLocaleString();
  document.getElementById('renewablePct').textContent = `${gridState.renewablePct}%`;
  document.getElementById('gridFreq').textContent = `${gridState.frequency.toFixed(3)} Hz`;

  // New Values
  document.getElementById('marketPrice').textContent = `$${gridState.marketPrice.toFixed(2)}`;
  document.getElementById('carbonIntensity').textContent = `${gridState.carbonIntensity}g`;
  document.getElementById('totalRevenue').textContent = Math.floor(gridState.totalRevenue).toLocaleString();

  // Bars (Assuming max capacity ~1500MW for scale)
  const maxScale = 1500;
  document.getElementById('demandBar').style.width = `${Math.min(100, (gridState.totalDemand / maxScale) * 100)}%`;
  document.getElementById('genBar').style.width = `${Math.min(100, (gridState.totalGen / maxScale) * 100)}%`;

  // Color coding frequency
  const freqElem = document.getElementById('gridFreq');
  if (gridState.frequency < 49.9 || gridState.frequency > 50.1) {
    freqElem.style.color = '#ff4f4f'; // Danger
  } else {
    freqElem.style.color = '#4caf50'; // Normal
  }
}

console.log('Cesium 3D map loaded with', bengaluruPlants.length, 'power plants');
