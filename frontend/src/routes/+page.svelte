<script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";

    let rows = 16;
    let columns = 16;
    let dotSize = 4;
    let dotColor = "#ffffff";
    let lineColor = "#ff6b6b";
    let facilityColor = "#00ff00";
    let connectionProbability = 0.75;
    let seed = 12345;
    let coverageRadius = 8; // Realistic urban ambulance response (8-10 minutes)
    let numFacilities = 3;
    let maxDemand = 100;
    let minTrafficWeight = 1;
    let maxTrafficWeight = 5;
    let mounted = false;
    let isCalculating = false;
    let calculationProgress = 0;
    let progressMessage = "";

    // Simple seeded random number generator (Linear Congruential Generator)
    function seededRandom(seed: number) {
        let state = seed;
        return function () {
            state = (state * 1664525 + 1013904223) % 4294967296;
            return state / 4294967296;
        };
    }

    function drawGrid() {
        // Only run in browser and after component is mounted
        if (!browser || !mounted) return;

        if (isCalculating) return; // Prevent multiple simultaneous calculations

        drawGridAsync();
    }

    // Optimized grid drawing with batch processing and reduced redundancy
    async function drawGridAsync() {
        isCalculating = true;
        calculationProgress = 0;
        progressMessage = "Starting calculation...";

        // Clear distance cache for new grid
        distanceCache.clear();

        const canvas = document.getElementById("myCanvas") as HTMLCanvasElement;
        if (!canvas) {
            isCalculating = false;
            return;
        }

        const ctx: CanvasRenderingContext2D = canvas.getContext(
            "2d",
        ) as CanvasRenderingContext2D;

        // Clear canvas with black background
        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Pre-calculate constants
        const spacingX = canvas.width / (columns + 1);
        const spacingY = canvas.height / (rows + 1);
        const totalPoints = rows * columns;

        // Create seeded random generators
        const random = seededRandom(seed);
        const demandRandom = seededRandom(seed + 1000);
        const trafficRandom = seededRandom(seed + 2000);

        // Pre-allocate arrays with known size
        const dotPositions: Array<{
            x: number;
            y: number;
            row: number;
            col: number;
            demand: number;
        }> = new Array(totalPoints);

        progressMessage = "Drawing dots...";
        calculationProgress = 10;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Batch dot creation and drawing
        ctx.fillStyle = dotColor;
        ctx.font = "10px Arial";
        ctx.textAlign = "center";

        let dotIndex = 0;
        for (let row = 1; row <= rows; row++) {
            for (let col = 1; col <= columns; col++) {
                const x = col * spacingX;
                const y = row * spacingY;
                const demand = Math.floor(demandRandom() * maxDemand) + 1;

                dotPositions[dotIndex] = { x, y, row, col, demand };

                // Draw dot
                ctx.beginPath();
                ctx.arc(x, y, dotSize, 0, 2 * Math.PI);
                ctx.fill();

                // Draw demand text
                ctx.fillStyle = "#888888";
                ctx.fillText(demand.toString(), x, y - dotSize - 2);
                ctx.fillStyle = dotColor;

                dotIndex++;
            }

            // Update progress every few rows
            if (row % 4 === 0) {
                calculationProgress = 10 + (row / rows) * 10;
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
        }

        progressMessage = "Creating connections...";
        calculationProgress = 20;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Optimized connection creation with Map pre-sizing
        const expectedConnections = Math.floor(
            totalPoints * connectionProbability * 2,
        );
        const connections = new Map<string, number>();

        // Batch connection processing
        let connectionCount = 0;
        for (let i = 0; i < totalPoints; i++) {
            const dot = dotPositions[i];

            // Horizontal connection
            if (dot.col < columns && random() < connectionProbability) {
                const connectionKey = getConnectionKey(
                    dot.row,
                    dot.col,
                    dot.row,
                    dot.col + 1,
                );
                const trafficWeight =
                    minTrafficWeight +
                    trafficRandom() * (maxTrafficWeight - minTrafficWeight);
                connections.set(connectionKey, trafficWeight);
                connectionCount++;
            }

            // Vertical connection
            if (dot.row < rows && random() < connectionProbability) {
                const connectionKey = getConnectionKey(
                    dot.row,
                    dot.col,
                    dot.row + 1,
                    dot.col,
                );
                const trafficWeight =
                    minTrafficWeight +
                    trafficRandom() * (maxTrafficWeight - minTrafficWeight);
                connections.set(connectionKey, trafficWeight);
                connectionCount++;
            }

            // Update progress every 100 dots
            if (i % 100 === 0) {
                calculationProgress = 20 + (i / totalPoints) * 10;
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
        }

        progressMessage = "Ensuring connectivity...";
        calculationProgress = 30;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Optimized connectivity check and enforcement
        await ensureConnectivity(connections, trafficRandom);

        progressMessage = "Drawing connections...";
        calculationProgress = 35;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Optimized connection drawing with batch processing
        await drawConnections(ctx, connections, dotPositions);

        progressMessage = "Solving facility placement with PSO...";
        calculationProgress = 50;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Solve Maximum Coverage Location Problem with optimized PSO
        const facilities = await solvePSOMaxCoverage(
            dotPositions,
            numFacilities,
            coverageRadius,
            connections,
        );

        progressMessage = "Drawing coverage areas...";
        calculationProgress = 80;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Optimized coverage visualization
        await drawCoverageAreas(ctx, facilities, dotPositions, connections);

        // Calculate and display statistics
        displayStatistics(ctx, facilities, dotPositions, connections);

        progressMessage = "Complete!";
        calculationProgress = 100;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        // Reset calculation state
        setTimeout(() => {
            isCalculating = false;
            calculationProgress = 0;
            progressMessage = "";
        }, 1000);
    }

    // Helper function for optimized connectivity ensuring
    async function ensureConnectivity(
        connections: Map<string, number>,
        trafficRandom: () => number,
    ) {
        const uf = new UnionFind();

        // Build union-find structure
        for (const connection of connections.keys()) {
            const [from, to] = connection.split("-");
            uf.union(from, to);
        }

        const components = uf.getComponents();

        if (components.size > 1) {
            const componentArray = Array.from(components);

            for (let i = 1; i < componentArray.length; i++) {
                // Find representatives more efficiently
                const dot1 = findRepresentative(componentArray[0], uf);
                const dot2 = findRepresentative(componentArray[i], uf);

                if (dot1 && dot2) {
                    const path = findPath(dot1, dot2);
                    for (let j = 0; j < path.length - 1; j++) {
                        const curr = path[j];
                        const next = path[j + 1];
                        const connectionKey = getConnectionKey(
                            curr.row,
                            curr.col,
                            next.row,
                            next.col,
                        );
                        connections.set(
                            connectionKey,
                            trafficRandom() *
                                (maxTrafficWeight - minTrafficWeight) +
                                minTrafficWeight,
                        );
                        uf.union(
                            `${curr.row},${curr.col}`,
                            `${next.row},${next.col}`,
                        );
                    }
                }

                if (i % 2 === 0) {
                    calculationProgress = 30 + (i / componentArray.length) * 5;
                    await new Promise((resolve) =>
                        requestAnimationFrame(resolve),
                    );
                }
            }
        }
    }

    // Helper function to find component representative
    function findRepresentative(
        component: string,
        uf: UnionFind,
    ): { row: number; col: number } | null {
        for (let row = 1; row <= rows; row++) {
            for (let col = 1; col <= columns; col++) {
                if (uf.find(`${row},${col}`) === component) {
                    return { row, col };
                }
            }
        }
        return null;
    }

    // Optimized connection drawing
    async function drawConnections(
        ctx: CanvasRenderingContext2D,
        connections: Map<string, number>,
        dotPositions: Array<{ x: number; y: number; row: number; col: number }>,
    ) {
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.font = "8px Arial";
        ctx.textAlign = "center";

        // Create position lookup for faster access
        const positionLookup = new Map<string, { x: number; y: number }>();
        for (const dot of dotPositions) {
            positionLookup.set(`${dot.row},${dot.col}`, { x: dot.x, y: dot.y });
        }

        let connectionIndex = 0;
        const totalConnections = connections.size;
        const weightRange = maxTrafficWeight - minTrafficWeight;

        for (const [connection, weight] of connections) {
            const [from, to] = connection.split("-");
            const fromPos = positionLookup.get(from);
            const toDot = positionLookup.get(to);

            if (fromPos && toDot) {
                // Optimized color calculation
                const normalizedWeight =
                    (weight - minTrafficWeight) / weightRange;
                const red = Math.floor(255 * normalizedWeight);
                const green = Math.floor(255 * (1 - normalizedWeight));
                ctx.strokeStyle = `rgb(${red}, ${green}, 0)`;

                // Draw connection
                ctx.beginPath();
                ctx.moveTo(fromPos.x, fromPos.y);
                ctx.lineTo(toDot.x, toDot.y);
                ctx.stroke();

                // Draw weight text
                const midX = (fromPos.x + toDot.x) / 2;
                const midY = (fromPos.y + toDot.y) / 2;
                ctx.fillStyle = "#ffffff";
                ctx.fillText(weight.toFixed(1), midX, midY);
            }

            // Update progress in larger batches
            if (connectionIndex % 50 === 0) {
                calculationProgress =
                    35 + (connectionIndex / totalConnections) * 15;
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
            connectionIndex++;
        }
    }

    // Optimized coverage area drawing
    async function drawCoverageAreas(
        ctx: CanvasRenderingContext2D,
        facilities: Array<{ row: number; col: number }>,
        dotPositions: Array<{ x: number; y: number; row: number; col: number }>,
        connections: Map<string, number>,
    ) {
        ctx.strokeStyle = facilityColor;
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 2;

        for (const facility of facilities) {
            const facilityDot = dotPositions.find(
                (d) => d.row === facility.row && d.col === facility.col,
            );
            if (facilityDot) {
                // Find covered dots efficiently
                const coveredDots = dotPositions.filter(
                    (dot) =>
                        calculateManhattanDistance(
                            facility,
                            dot,
                            connections,
                        ) <= coverageRadius,
                );

                if (coveredDots.length > 0) {
                    ctx.fillStyle = facilityColor + "20";
                    ctx.beginPath();

                    const boundaryDots = findCoverageBoundary(
                        coveredDots,
                        facility,
                        coverageRadius,
                        connections,
                    );

                    if (boundaryDots.length > 0) {
                        ctx.moveTo(boundaryDots[0].x, boundaryDots[0].y);
                        for (let i = 1; i < boundaryDots.length; i++) {
                            ctx.lineTo(boundaryDots[i].x, boundaryDots[i].y);
                        }
                        ctx.closePath();
                        ctx.fill();
                        ctx.stroke();

                        // Draw red borders around boundary dots
                        ctx.strokeStyle = "#ff0000";
                        ctx.lineWidth = 2;
                        ctx.fillStyle = facilityColor + "80"; // Semi-transparent facility color

                        for (const dot of boundaryDots) {
                            ctx.beginPath();
                            ctx.arc(dot.x, dot.y, dotSize + 1, 0, 2 * Math.PI);
                            ctx.fill();
                            ctx.stroke();
                        }

                        // Restore previous stroke style for facility color
                        ctx.strokeStyle = facilityColor;
                        ctx.lineWidth = 2;
                    }
                }
            }
        }

        // Draw facilities
        ctx.setLineDash([]);
        ctx.fillStyle = facilityColor;
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 2;

        for (const facility of facilities) {
            const facilityDot = dotPositions.find(
                (d) => d.row === facility.row && d.col === facility.col,
            );
            if (facilityDot) {
                ctx.beginPath();
                ctx.arc(
                    facilityDot.x,
                    facilityDot.y,
                    dotSize + 3,
                    0,
                    2 * Math.PI,
                );
                ctx.fill();
                ctx.stroke();
            }
        }
    }

    // Optimized statistics calculation and display
    function displayStatistics(
        ctx: CanvasRenderingContext2D,
        facilities: Array<{ row: number; col: number }>,
        dotPositions: Array<{
            x: number;
            y: number;
            row: number;
            col: number;
            demand: number;
        }>,
        connections: Map<string, number>,
    ) {
        const totalDemand = dotPositions.reduce(
            (sum, dot) => sum + dot.demand,
            0,
        );
        let coveredDemand = 0;
        let coveredPoints = 0;

        // Optimize coverage calculation
        for (const dot of dotPositions) {
            const isCovered = facilities.some(
                (facility) =>
                    calculateManhattanDistance(dot, facility, connections) <=
                    coverageRadius,
            );
            if (isCovered) {
                coveredDemand += dot.demand;
                coveredPoints++;
            }
        }

        // Display statistics
        ctx.fillStyle = "#ffffff";
        ctx.font = "14px Arial";
        ctx.textAlign = "left";
        const stats = [
            `Total Demand: ${totalDemand}`,
            `Covered Demand: ${coveredDemand}`,
            `Coverage: ${((coveredDemand / totalDemand) * 100).toFixed(1)}%`,
            `Points Covered: ${coveredPoints}/${dotPositions.length}`,
            `Facilities: ${facilities.length}`,
            `Method: Optimized PSO`,
            `Radius: ${coverageRadius} (Manhattan)`,
        ];

        stats.forEach((stat, index) => {
            ctx.fillText(stat, 10, 25 + index * 20);
        });
    }

    // Optimized distance calculation with caching and proper priority queue
    const distanceCache = new Map<string, number>();

    function calculateManhattanDistance(
        from: { row: number; col: number },
        to: { row: number; col: number },
        connections: Map<string, number>,
    ): number {
        const cacheKey = `${from.row},${from.col}-${to.row},${to.col}`;

        // Check cache first
        if (distanceCache.has(cacheKey)) {
            return distanceCache.get(cacheKey)!;
        }

        // Early exit for same point
        if (from.row === to.row && from.col === to.col) {
            distanceCache.set(cacheKey, 0);
            return 0;
        }

        // Use A* algorithm with Manhattan heuristic for better performance
        const distances = new Map<string, number>();
        const visited = new Set<string>();

        // Priority queue using binary heap for O(log n) operations
        const heap = new MinHeap<{
            node: string;
            distance: number;
            priority: number;
        }>();

        const startKey = `${from.row},${from.col}`;
        const endKey = `${to.row},${to.col}`;

        // Heuristic function (Manhattan distance)
        const heuristic = (row: number, col: number) =>
            Math.abs(row - to.row) + Math.abs(col - to.col);

        distances.set(startKey, 0);
        heap.push({
            node: startKey,
            distance: 0,
            priority: heuristic(from.row, from.col),
        });

        while (!heap.isEmpty()) {
            const current = heap.pop()!;

            if (visited.has(current.node)) continue;
            visited.add(current.node);

            if (current.node === endKey) {
                distanceCache.set(cacheKey, current.distance);
                return current.distance;
            }

            const [currentRow, currentCol] = current.node
                .split(",")
                .map(Number);

            // Pre-calculate neighbor coordinates to avoid repeated calculations
            const neighbors = [
                [currentRow - 1, currentCol],
                [currentRow + 1, currentCol],
                [currentRow, currentCol - 1],
                [currentRow, currentCol + 1],
            ];

            for (const [row, col] of neighbors) {
                if (row < 1 || row > rows || col < 1 || col > columns) continue;

                const neighborKey = `${row},${col}`;
                if (visited.has(neighborKey)) continue;

                const connectionKey = getConnectionKey(
                    currentRow,
                    currentCol,
                    row,
                    col,
                );

                if (connections.has(connectionKey)) {
                    const edgeWeight = connections.get(connectionKey)!;
                    const newDistance = current.distance + edgeWeight;
                    const currentBest = distances.get(neighborKey) ?? Infinity;

                    if (newDistance < currentBest) {
                        distances.set(neighborKey, newDistance);
                        heap.push({
                            node: neighborKey,
                            distance: newDistance,
                            priority: newDistance + heuristic(row, col),
                        });
                    }
                }
            }
        }

        const result = distances.get(endKey) ?? Infinity;
        distanceCache.set(cacheKey, result);
        return result;
    }

    // Binary heap implementation for efficient priority queue
    class MinHeap<T extends { priority: number }> {
        private items: T[] = [];

        push(item: T): void {
            this.items.push(item);
            this.heapifyUp(this.items.length - 1);
        }

        pop(): T | undefined {
            if (this.items.length === 0) return undefined;
            if (this.items.length === 1) return this.items.pop();

            const result = this.items[0];
            this.items[0] = this.items.pop()!;
            this.heapifyDown(0);
            return result;
        }

        isEmpty(): boolean {
            return this.items.length === 0;
        }

        private heapifyUp(index: number): void {
            while (index > 0) {
                const parentIndex = Math.floor((index - 1) / 2);
                if (
                    this.items[parentIndex].priority <=
                    this.items[index].priority
                )
                    break;

                [this.items[parentIndex], this.items[index]] = [
                    this.items[index],
                    this.items[parentIndex],
                ];
                index = parentIndex;
            }
        }

        private heapifyDown(index: number): void {
            while (true) {
                let smallest = index;
                const leftChild = 2 * index + 1;
                const rightChild = 2 * index + 2;

                if (
                    leftChild < this.items.length &&
                    this.items[leftChild].priority <
                        this.items[smallest].priority
                ) {
                    smallest = leftChild;
                }

                if (
                    rightChild < this.items.length &&
                    this.items[rightChild].priority <
                        this.items[smallest].priority
                ) {
                    smallest = rightChild;
                }

                if (smallest === index) break;

                [this.items[index], this.items[smallest]] = [
                    this.items[smallest],
                    this.items[index],
                ];
                index = smallest;
            }
        }
    }

    // Optimized boundary finding with spatial indexing
    function findCoverageBoundary(
        coveredDots: Array<{ x: number; y: number; row: number; col: number }>,
        facility: { row: number; col: number },
        radius: number,
        connections: Map<string, number>,
    ) {
        if (coveredDots.length === 0) return [];

        // Use spatial indexing for faster boundary detection
        const gridCoverage = new Set<string>();
        const boundaryPoints = new Set<string>();

        // Pre-calculate coverage area bounds
        const minRow = Math.max(1, facility.row - Math.ceil(radius));
        const maxRow = Math.min(rows, facility.row + Math.ceil(radius));
        const minCol = Math.max(1, facility.col - Math.ceil(radius));
        const maxCol = Math.min(columns, facility.col + Math.ceil(radius));

        // Build coverage set efficiently
        for (let r = minRow; r <= maxRow; r++) {
            for (let c = minCol; c <= maxCol; c++) {
                const key = `${r},${c}`;
                // Use cached distance calculation
                const distance = calculateManhattanDistance(
                    facility,
                    { row: r, col: c },
                    connections,
                );
                if (distance <= radius) {
                    gridCoverage.add(key);
                }
            }
        }

        // Find boundary points using efficient neighbor checking
        const spacingX = 768 / (columns + 1);
        const spacingY = 768 / (rows + 1);
        const boundaryDots: Array<{
            x: number;
            y: number;
            row: number;
            col: number;
        }> = [];

        for (let r = minRow; r <= maxRow; r++) {
            for (let c = minCol; c <= maxCol; c++) {
                const key = `${r},${c}`;
                if (gridCoverage.has(key)) {
                    // Check if this is a boundary point (has neighbor outside coverage)
                    const neighbors = [
                        `${r - 1},${c}`,
                        `${r + 1},${c}`,
                        `${r},${c - 1}`,
                        `${r},${c + 1}`,
                    ];

                    const isBoundary = neighbors.some(
                        (neighbor) => !gridCoverage.has(neighbor),
                    );

                    if (isBoundary) {
                        boundaryDots.push({
                            x: c * spacingX,
                            y: r * spacingY,
                            row: r,
                            col: c,
                        });
                    }
                }
            }
        }

        // Optimize polygon sorting using more efficient angle calculation
        if (boundaryDots.length > 0) {
            const facilityX = facility.col * spacingX;
            const facilityY = facility.row * spacingY;

            // Use faster sorting with pre-calculated angles
            const angledPoints = boundaryDots.map((dot) => ({
                ...dot,
                angle: Math.atan2(dot.y - facilityY, dot.x - facilityX),
            }));

            angledPoints.sort((a, b) => a.angle - b.angle);
            return angledPoints;
        }

        return boundaryDots;
    }

    // Optimized Union-Find data structure for connectivity
    class UnionFind {
        private parent: Map<string, string>;
        private rank: Map<string, number>;

        constructor() {
            this.parent = new Map();
            this.rank = new Map();
        }

        find(x: string): string {
            if (!this.parent.has(x)) {
                this.parent.set(x, x);
                this.rank.set(x, 0);
                return x;
            }

            // Path compression optimization
            const parentX = this.parent.get(x)!;
            if (parentX !== x) {
                const root = this.find(parentX);
                this.parent.set(x, root);
                return root;
            }
            return x;
        }

        union(x: string, y: string): boolean {
            const rootX = this.find(x);
            const rootY = this.find(y);

            if (rootX === rootY) return false;

            const rankX = this.rank.get(rootX)!;
            const rankY = this.rank.get(rootY)!;

            // Union by rank optimization
            if (rankX < rankY) {
                this.parent.set(rootX, rootY);
            } else if (rankX > rankY) {
                this.parent.set(rootY, rootX);
            } else {
                this.parent.set(rootY, rootX);
                this.rank.set(rootX, rankX + 1);
            }
            return true;
        }

        getComponents(): Set<string> {
            const components = new Set<string>();
            for (let row = 1; row <= rows; row++) {
                for (let col = 1; col <= columns; col++) {
                    components.add(this.find(`${row},${col}`));
                }
            }
            return components;
        }
    }

    // Optimized path finding with early termination
    function findPath(
        start: { row: number; col: number },
        end: { row: number; col: number },
    ): Array<{ row: number; col: number }> {
        const path: Array<{ row: number; col: number }> = [];
        let current = { ...start };

        // Move horizontally first, then vertically (Manhattan path)
        while (current.col !== end.col) {
            path.push({ ...current });
            current.col += end.col > current.col ? 1 : -1;
        }

        while (current.row !== end.row) {
            path.push({ ...current });
            current.row += end.row > current.row ? 1 : -1;
        }

        path.push({ ...current }); // Add final position
        return path;
    }

    // Optimized PSO with early termination and better swarm management
    async function solvePSOMaxCoverage(
        points: Array<{ row: number; col: number; demand: number }>,
        numFacilities: number,
        radius: number,
        connections: Map<string, number>,
    ) {
        const swarmSize = Math.min(20, points.length); // Adaptive swarm size
        const maxIterations = 30; // Reduced iterations with better convergence
        const w = 0.729; // Optimized inertia weight (Clerc & Kennedy)
        const c1 = 1.49445; // Optimized cognitive parameter
        const c2 = 1.49445; // Optimized social parameter

        // Initialize random number generator for PSO
        const psoRandom = seededRandom(seed + 5000);

        // Pre-calculate total demand for normalization
        const totalDemand = points.reduce((sum, p) => sum + p.demand, 0);

        // Optimized particle class with better memory management
        // svelte-ignore perf_avoid_nested_class
        class Particle {
            position: number[];
            velocity: number[];
            bestPosition: number[];
            bestFitness: number;
            fitness: number;
            stagnationCounter: number;

            constructor() {
                this.position = new Array(numFacilities);
                this.velocity = new Array(numFacilities);
                this.bestPosition = new Array(numFacilities);
                this.bestFitness = -Infinity;
                this.fitness = 0;
                this.stagnationCounter = 0;

                // Initialize with diverse positions using better distribution
                const used = new Set<number>();
                for (let i = 0; i < numFacilities; i++) {
                    let pos: number;
                    do {
                        pos = Math.floor(psoRandom() * points.length);
                    } while (used.has(pos));

                    this.position[i] = pos;
                    this.velocity[i] =
                        (psoRandom() - 0.5) * points.length * 0.1;
                    used.add(pos);
                }
                this.bestPosition = [...this.position];
            }

            updateVelocity(
                globalBest: number[],
                iteration: number,
                maxIter: number,
            ) {
                // Adaptive parameters
                const adaptiveW = (w * (maxIter - iteration)) / maxIter;

                for (let i = 0; i < numFacilities; i++) {
                    const r1 = psoRandom();
                    const r2 = psoRandom();

                    this.velocity[i] =
                        adaptiveW * this.velocity[i] +
                        c1 * r1 * (this.bestPosition[i] - this.position[i]) +
                        c2 * r2 * (globalBest[i] - this.position[i]);

                    // Velocity clamping
                    const maxVel = points.length * 0.1;
                    this.velocity[i] = Math.max(
                        -maxVel,
                        Math.min(maxVel, this.velocity[i]),
                    );
                }
            }

            updatePosition() {
                for (let i = 0; i < numFacilities; i++) {
                    this.position[i] += this.velocity[i];
                    this.position[i] = Math.max(
                        0,
                        Math.min(
                            points.length - 1,
                            Math.round(this.position[i]),
                        ),
                    );
                }

                // Remove duplicates efficiently
                const used = new Set<number>();
                for (let i = 0; i < numFacilities; i++) {
                    let pos = Math.round(this.position[i]);
                    let attempts = 0;
                    while (used.has(pos) && attempts < points.length) {
                        pos = (pos + 1) % points.length;
                        attempts++;
                    }
                    this.position[i] = pos;
                    used.add(pos);
                }
            }

            evaluateFitness() {
                const facilities = this.position.map(
                    (idx) => points[Math.round(idx)],
                );
                let totalCoverage = 0;
                const coveredPoints = new Set<string>();

                // Use optimized coverage calculation
                for (const point of points) {
                    const pointKey = `${point.row},${point.col}`;
                    if (!coveredPoints.has(pointKey)) {
                        for (const facility of facilities) {
                            const distance = calculateManhattanDistance(
                                point,
                                facility,
                                connections,
                            );
                            if (distance <= radius) {
                                totalCoverage += point.demand;
                                coveredPoints.add(pointKey);
                                break; // Point is covered, no need to check other facilities
                            }
                        }
                    }
                }

                this.fitness = totalCoverage;

                if (this.fitness > this.bestFitness) {
                    this.bestFitness = this.fitness;
                    this.bestPosition = [...this.position];
                    this.stagnationCounter = 0;
                } else {
                    this.stagnationCounter++;
                }
            }
        }

        // Initialize swarm with better diversity
        const swarm: Particle[] = Array(swarmSize)
            .fill(null)
            .map(() => new Particle());

        // Evaluate initial fitness
        progressMessage = "Initializing PSO swarm...";
        await Promise.all(
            swarm.map((particle, i) => {
                return new Promise<void>((resolve) => {
                    particle.evaluateFitness();
                    if (i % 5 === 0) {
                        calculationProgress = 50 + (i / swarmSize) * 5;
                    }
                    resolve();
                });
            }),
        );

        // Find global best
        let globalBest = [...swarm[0].bestPosition];
        let globalBestFitness = swarm[0].bestFitness;
        let stagnationCount = 0;

        for (const particle of swarm) {
            if (particle.bestFitness > globalBestFitness) {
                globalBestFitness = particle.bestFitness;
                globalBest = [...particle.bestPosition];
            }
        }

        // PSO main loop with early termination
        let iteration = 0;
        while (iteration < maxIterations) {
            progressMessage = `PSO Iteration ${iteration + 1}/${maxIterations}`;

            const prevGlobalBest = globalBestFitness;

            // Process particles in batches for better progress tracking
            const batchSize = Math.ceil(swarmSize / 4);
            for (let batch = 0; batch < swarmSize; batch += batchSize) {
                const batchEnd = Math.min(batch + batchSize, swarmSize);

                for (let i = batch; i < batchEnd; i++) {
                    const particle = swarm[i];
                    particle.updateVelocity(
                        globalBest,
                        iteration,
                        maxIterations,
                    );
                    particle.updatePosition();
                    particle.evaluateFitness();

                    if (particle.bestFitness > globalBestFitness) {
                        globalBestFitness = particle.bestFitness;
                        globalBest = [...particle.bestPosition];
                        stagnationCount = 0;
                    }
                }

                calculationProgress =
                    55 +
                    (iteration / maxIterations) * 20 +
                    (batch / swarmSize) * (20 / maxIterations);
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }

            // Check for convergence
            if (globalBestFitness === prevGlobalBest) {
                stagnationCount++;
            }

            // Early termination conditions
            if (
                stagnationCount > 5 ||
                globalBestFitness >= totalDemand * 0.95
            ) {
                break;
            }

            iteration++;
        }

        // Convert best solution to facility coordinates
        const bestFacilities = globalBest.map((idx) => {
            const point = points[Math.round(idx)];
            return { row: point.row, col: point.col };
        });

        progressMessage = "PSO optimization complete!";
        calculationProgress = 75;
        await new Promise((resolve) => requestAnimationFrame(resolve));

        return bestFacilities;
    }

    // Optimized connection key generation
    function getConnectionKey(
        r1: number,
        c1: number,
        r2: number,
        c2: number,
    ): string {
        // Use bitwise operations for faster comparison
        return r1 < r2 || (r1 === r2 && c1 < c2)
            ? `${r1},${c1}-${r2},${c2}`
            : `${r2},${c2}-${r1},${c1}`;
    }

    onMount(() => {
        mounted = true;
        // Add small delay to ensure DOM is ready
        setTimeout(drawGrid, 100);
    });

    // Debounced update function to prevent excessive recalculations
    let updateTimeout: number;
    function updateGrid() {
        if (updateTimeout) clearTimeout(updateTimeout);
        updateTimeout = setTimeout(drawGrid, 150);
    }
</script>

<nav style="background:#0d1626;border-bottom:1px solid #1e2d3d;padding:12px 20px;display:flex;align-items:center;gap:20px;font-family:'Syne',sans-serif">
    <span style="font-weight:800;color:#f0f6ff;font-size:15px">🚑 Ambulance System</span>
    <a href="/" style="color:#6366f1;text-decoration:none;font-size:13px;font-weight:600">Grid Simulator</a>
    <a href="/dashboard" style="color:#94a3b8;text-decoration:none;font-size:13px;font-weight:600;background:#1e2d3d;padding:6px 14px;border-radius:6px">📊 India/Kolkata Dashboard</a>
    <a href="/map" style="color:#94a3b8;text-decoration:none;font-size:13px;font-weight:600">🗺 Map</a>
</nav>

<div class="container">
    <div class="controls">
        <h2>Grid Controls</h2>
        <div class="control-group">
            <label for="rows">Rows:</label>
            <input id="rows" type="range" min="1" max="50" bind:value={rows} />
            <span>{rows}</span>
        </div>

        <div class="control-group">
            <label for="columns">Columns:</label>
            <input
                id="columns"
                type="range"
                min="1"
                max="50"
                bind:value={columns}
            />
            <span>{columns}</span>
        </div>

        <div class="control-group">
            <label for="dotSize">Dot Size:</label>
            <input
                id="dotSize"
                type="range"
                min="1"
                max="20"
                bind:value={dotSize}
            />
            <span>{dotSize}px</span>
        </div>

        <div class="control-group">
            <label for="dotColor">Dot Color:</label>
            <input id="dotColor" type="color" bind:value={dotColor} />
        </div>

        <div class="control-group">
            <label for="lineColor">Line Color:</label>
            <input id="lineColor" type="color" bind:value={lineColor} />
        </div>

        <div class="control-group">
            <label for="connectionProbability">Connection Probability:</label>
            <input
                id="connectionProbability"
                type="range"
                min="0"
                max="1"
                step="0.05"
                bind:value={connectionProbability}
            />
            <span>{Math.round(connectionProbability * 100)}%</span>
        </div>

        <div class="control-group">
            <label for="seed">Random Seed:</label>
            <input
                id="seed"
                type="number"
                min="1"
                max="999999"
                bind:value={seed}
            />
        </div>

        <hr style="margin: 20px 0; border: 1px solid #ddd;" />

        <h3 style="margin: 10px 0; color: #333;">Coverage Problem</h3>

        <div class="control-group">
            <label for="numFacilities">Number of Facilities:</label>
            <input
                id="numFacilities"
                type="range"
                min="1"
                max="10"
                bind:value={numFacilities}
            />
            <span>{numFacilities}</span>
        </div>

        <div class="control-group">
            <label for="coverageRadius">Coverage Radius:</label>
            <input
                id="coverageRadius"
                type="range"
                min="1"
                max="8"
                step="0.5"
                bind:value={coverageRadius}
            />
            <span>{coverageRadius}</span>
        </div>

        <div class="control-group">
            <label for="minTrafficWeight">Min Traffic Weight:</label>
            <input
                id="minTrafficWeight"
                type="range"
                min="0.5"
                max="3"
                step="0.1"
                bind:value={minTrafficWeight}
            />
            <span>{minTrafficWeight.toFixed(1)}</span>
        </div>

        <div class="control-group">
            <label for="maxTrafficWeight">Max Traffic Weight:</label>
            <input
                id="maxTrafficWeight"
                type="range"
                min="2"
                max="10"
                step="0.1"
                bind:value={maxTrafficWeight}
            />
            <span>{maxTrafficWeight.toFixed(1)}</span>
        </div>

        <div class="control-group">
            <label for="maxDemand">Max Demand per Point:</label>
            <input
                id="maxDemand"
                type="range"
                min="10"
                max="200"
                step="10"
                bind:value={maxDemand}
            />
            <span>{maxDemand}</span>
        </div>

        <div class="control-group">
            <label for="facilityColor">Facility Color:</label>
            <input id="facilityColor" type="color" bind:value={facilityColor} />
        </div>

        <hr style="margin: 20px 0; border: 1px solid #ddd;" />

        <div class="control-group">
            <button
                class="update-btn"
                on:click={updateGrid}
                disabled={isCalculating}
            >
                {isCalculating ? "Calculating..." : "Update Grid"}
            </button>
        </div>

        {#if isCalculating}
            <div class="progress-container">
                <div class="progress-label">{progressMessage}</div>
                <div class="progress-bar">
                    <div
                        class="progress-fill"
                        style="width: {calculationProgress}%"
                    ></div>
                </div>
                <div class="progress-percentage">
                    {Math.round(calculationProgress)}%
                </div>
            </div>
        {/if}
    </div>

    <canvas id="myCanvas" width="768" height="768"></canvas>
</div>

<style>
    .container {
        display: flex;
        gap: 20px;
        padding: 20px;
        align-items: flex-start;
        height: 100vh;
    }

    .controls {
        background: #f5f5f5;
        padding: 20px;
        border-radius: 8px;
        min-width: 250px;
        max-width: 300px;
        height: calc(100vh - 40px);
        overflow-y: auto;
        flex-shrink: 0;
    }

    .controls h2 {
        margin-top: 0;
        color: #333;
    }

    .control-group {
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin-bottom: 15px;
    }

    .control-group label {
        font-weight: bold;
        color: #555;
        display: flex;
        align-items: center;
    }

    .control-group input[type="range"] {
        width: 100%;
    }

    .control-group span {
        color: #666;
        font-size: 14px;
    }

    canvas {
        border: 2px solid #333;
        border-radius: 4px;
        position: fixed;
        right: 20px;
        top: 20px;
        z-index: 10;
    }

    .update-btn {
        background: #007acc;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        width: 100%;
        transition: background-color 0.2s;
    }

    .update-btn:hover {
        background: #005a9e;
    }

    .update-btn:active {
        background: #004785;
        transform: translateY(1px);
    }

    .update-btn:disabled {
        background: #cccccc;
        cursor: not-allowed;
        transform: none;
    }

    .progress-container {
        margin-top: 20px;
        padding: 15px;
        background: #ffffff;
        border-radius: 8px;
        border: 1px solid #ddd;
    }

    .progress-label {
        font-size: 14px;
        font-weight: bold;
        color: #333;
        margin-bottom: 8px;
        text-align: center;
    }

    .progress-bar {
        width: 100%;
        height: 20px;
        background: #f0f0f0;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 5px;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #007acc, #00a0ff);
        border-radius: 10px;
        transition: width 0.3s ease;
        position: relative;
    }

    .progress-fill::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.3),
            transparent
        );
        animation: shimmer 2s infinite;
    }

    @keyframes shimmer {
        0% {
            transform: translateX(-100%);
        }
        100% {
            transform: translateX(100%);
        }
    }

    .progress-percentage {
        text-align: center;
        font-size: 12px;
        color: #666;
        font-weight: bold;
    }
</style>