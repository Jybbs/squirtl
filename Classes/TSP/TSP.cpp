#include <algorithm>
#include <chrono>
#include <climits>
#include <iomanip>
#include <iostream>
#include <random>
#include <vector>

using namespace std;

#define INF INT_MAX

/*
 * Traveling Salesman Problem (TSP) using Dynamic Programming
 * 
 * Problem Classification:
 * - This implementation solves the symmetric Traveling Salesman Problem (TSP), which is classified as NP-hard.
 * - It implements the Held-Karp algorithm, a dynamic programming solution to the TSP.
 * 
 * Held-Karp Algorithm:
 * - An exacting algorithm that solves the TSP in O(n^2 * 2^n) time, which is significantly faster than 
 *   the naive O(n!) approach but still exponential.
 * 
 * Dynamic Programming Approach:
 * - The algorithm uses dynamic programming with bitmasks to solve subproblems and build up to the final solution.
 * - This approach allows for memoization of intermediate results, significantly reducing redundant computations.
 * - This implementation assumes a symmetric TSP, where the distance from point A to B is the same as from B to A.
 * 
 * Space Complexity:
 * - The space complexity is O(n * 2^n) due to the memoization table used in the dynamic programming approach.
 * 
 * Limitations:
 * - While this algorithm finds the optimal solution, its exponential time complexity makes it impractical 
 *   for very large instances (typically more than 20-25 cities).
 * - For larger instances, approximation algorithms or heuristics are often used instead.
 * 
 */
int tsp(int mask, int pos, const vector<vector<int>> &dist, vector<vector<int>> &dp, int n)
{
    if (mask == (1 << n) - 1)
    {
        return dist[pos][0];
    }

    if (dp[mask][pos] != -1)
    {
        return dp[mask][pos];
    }

    int ans = INF;

    for (int address = 0; address < n; ++address)
    {
        if ((mask & (1 << address)) == 0)
        {
            int newAns = dist[pos][address] + tsp(mask | (1 << address), address, dist, dp, n);
            ans = min(ans, newAns);
        }
    }

    return dp[mask][pos] = ans;
}

/*
 * This function initializes the DP table with -1 to indicate uncalculated states.
 * Initialization is crucial to ensure that all subproblems are correctly identified as unsolved
 * at the start of the algorithm. The DP table is used to store the results of subproblems.
 *
 * Parameters:
 * - dp: Memoization table. This is a key component of dynamic programming, storing the results
 *   of subproblems to avoid redundant calculations.
 * - n: Total number of addresses. This is required to initialize the DP table to the correct size.
 */
void initializeDPTable(vector<vector<int>> &dp, int n)
{
    for (int i = 0; i < (1 << n); ++i)
    {
        for (int j = 0; j < n; ++j)
        {
            dp[i][j] = -1;
        }
    }
}

/*
 * This function prints the distance matrix for verification.
 * Printing the distance matrix is useful for debugging and verifying that the input
 * has been correctly interpreted.
 *
 * Parameters:
 * - dist: Distance matrix between addresses. This contains the distances between all pairs of addresses.
 * - n: Total number of addresses. This is required to correctly iterate through the distance matrix.
 */
void printDistanceMatrix(const vector<vector<int>> &dist, int n)
{
    cout << "Distance Matrix:" << endl;
    for (int i = 0; i < n; ++i)
    {
        for (int j = 0; j < n; ++j)
        {
            if (dist[i][j] == INF)
            {
                cout << "INF ";
            }
            else
            {
                cout << dist[i][j] << " ";
            }
        }
        cout << endl;
    }
}

/*
 * This function prints the final result, the minimum cost.
 * Printing the result allows us to see the outcome of the TSP algorithm, which is the minimum cost
 * of visiting all addresses and returning to the start.
 *
 * Parameters:
 * - result: The minimum cost of visiting all addresses and returning to the start.
 */
void printResult(int result)
{
    cout << "The minimum cost of visiting all addresses and returning to the start is: " << result << endl;
}

int main() {
    /*
     * Traveling Salesman Problem (TSP) Solver using Dynamic Programming
     * 
     * This implementation solves the symmetric Traveling Salesman Problem (TSP) using the Held-Karp algorithm.
     * The TSP is NP-hard, meaning no known polynomial-time algorithm exists to solve it optimally for all instances.
     * 
     * Problem Description:
     * - We have 10 cities, numbered from 0 to 9.
     * - The goal is to find the shortest possible route that visits each city exactly once and returns to the starting city.
     * - The distances between cities are randomly generated to simulate real-world variability.
     * 
     * Algorithm:
     * - Uses dynamic programming with bitmasks to solve subproblems and build up to the final solution.
     * - Time complexity: O(n^2 * 2^n), where n is the number of cities.
     * - Space complexity: O(n * 2^n) due to the memoization table.
     * 
     * This approach is suitable for small to medium-sized instances (up to about 20-25 cities) where finding 
     * the exact optimal solution is crucial. For larger instances, heuristic methods are often preferred.
     */

    int n = 10; // Number of cities

    // Generate a random distance matrix
    vector<vector<int>> dist(n, vector<int>(n, 0));
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> distrib(10, 100); // Distances between 10 and 100 units

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int distance = distrib(gen);
            dist[i][j] = distance;
            dist[j][i] = distance; // Ensure symmetry
        }
    }

    // Initialize DP table
    vector<vector<int>> dp(1 << n, vector<int>(n, -1));

    // Print the distance matrix
    cout << "Distance Matrix for 10 Cities\n" << endl;
    printDistanceMatrix(dist, n);

    // Solve the TSP problem and measure execution time
    auto start = chrono::high_resolution_clock::now();
    int result = tsp(1, 0, dist, dp, n);
    auto end = chrono::high_resolution_clock::now();

    // Print the result
    cout << "\nTSP Solution:" << endl;
    printResult(result);

    // Print execution time
    chrono::duration<double> duration = end - start;
    cout << "Execution time: " << fixed << setprecision(6) << duration.count() << " seconds" << endl;

    return 0;
}
