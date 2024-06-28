#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

using namespace std;

#define INF INT_MAX

/*
 * This function solves the Traveling Salesman Problem using Dynamic Programming and Bit Masking.
 * It calculates the minimum cost of visiting all event addresses starting from a given address
 * with a given mask of visited addresses.
 *
 * The function works as follows:
 * 1. If all addresses have been visited (base case), it returns the distance from the current
 *    address back to the starting address. This is necessary to complete the tour and return to the start.
 * 2. If the subproblem has already been solved, it returns the stored result from the memoization table.
 *    This avoids redundant calculations and improves efficiency.
 * 3. Otherwise, it iterates through all unvisited addresses, calculates the cost of visiting each,
 *    and updates the minimum cost. This explores all possible paths to find the optimal solution.
 *
 * Parameters:
 * - mask: Bitmask representing the set of visited addresses. This helps keep track of which addresses
 *   have been visited in the current state of the problem.
 * - pos: Current address position. This is required to know from where we are calculating the next step.
 * - dist: Distance matrix between addresses. This contains the distances between all pairs of addresses
 *   and is essential for calculating the cost of traveling between them.
 * - dp: Memoization table. This stores results of subproblems to avoid redundant calculations and improve efficiency.
 * - n: Total number of addresses. This is required to iterate through all addresses and manage the bitmask.
 *
 * Returns:
 * - The minimum cost of visiting all addresses and returning to the start.
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

int main()
{
    /*
     * Example scenario:
     * Suppose we have 4 event addresses in the game, represented as follows:
     * Address 0: Starting point
     * Address 1: Event 1
     * Address 2: Event 2
     * Address 3: Event 3
     *
     * Distance matrix representation (using INF for unreachable paths):
     *      0    1    2    3
     * 0 [  0,  10,  15,  20 ]
     * 1 [ 10,   0,  35,  25 ]
     * 2 [ 15,  35,   0,  30 ]
     * 3 [ 20,  25,  30,   0 ]
     *
     * This example helps to illustrate the functionality of the TSP algorithm
     * with a concrete set of distances between addresses.
     */

    int n = 4; // Number of addresses

    // Distance matrix
    vector<vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}};

    // Initialize DP table
    vector<vector<int>> dp(1 << n, vector<int>(n));
    initializeDPTable(dp, n);

    // Print the distance matrix
    printDistanceMatrix(dist, n);

    // Solve the TSP problem
    int result = tsp(1, 0, dist, dp, n);

    // Print the result
    printResult(result);

    return 0;
}
