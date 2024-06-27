#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <stdexcept>

using namespace std;

class PCA
{
private:
    int numComponents;
    vector<vector<double>> principalComponents;

    vector<vector<double>> centerData(const vector<vector<double>>& data)
    {
        int numSamples = data.size();
        int numFeatures = data[0].size();
        vector<double> featureMeans(numFeatures, 0.0);

        // Calculate the mean of each feature
        // Centering is crucial because PCA is sensitive to the relative scaling of the original variables
        for (const auto& sample : data)
        {
            for (int i = 0; i < numFeatures; ++i)
            {
                featureMeans[i] += sample[i];
            }
        }
        for (int i = 0; i < numFeatures; ++i)
        {
            featureMeans[i] /= numSamples;
        }

        // Subtract the mean from each data point
        // This step ensures that the first principal component corresponds to the direction of maximum variance
        // Without centering, the first component might be dominated by the mean of the data
        vector<vector<double>> centeredData(numSamples, vector<double>(numFeatures, 0.0));
        for (int i = 0; i < numSamples; ++i)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                centeredData[i][j] = data[i][j] - featureMeans[j];
            }
        }
        return centeredData;
    }

    vector<vector<double>> computeCovarianceMatrix(const vector<vector<double>>& centeredData)
    {
        int numSamples = centeredData.size();
        int numFeatures = centeredData[0].size();
        vector<vector<double>> covarianceMatrix(numFeatures, vector<double>(numFeatures, 0.0));

        // Calculate covariance between each pair of features
        // The covariance matrix is symmetric, so we could optimize by only computing half
        // Covariance measures how much two variables change together
        // High absolute values indicate strong relationships (positive or negative)
        for (int i = 0; i < numFeatures; ++i)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                for (int k = 0; k < numSamples; ++k)
                {
                    covarianceMatrix[i][j] += centeredData[k][i] * centeredData[k][j];
                }
                
                // Divide by (n-1) for sample covariance (unbiased estimator)
                // This correction is important for small sample sizes
                covarianceMatrix[i][j] /= (numSamples - 1);
            }
        }
        return covarianceMatrix;
    }

    pair<vector<double>, vector<vector<double>>> computeEigenvectors(const vector<vector<double>>& originalCovarianceMatrix)
    {
        int numFeatures = originalCovarianceMatrix.size();
        vector<vector<double>> eigenvectors(numFeatures, vector<double>(numFeatures, 0.0));
        vector<double> eigenvalues(numFeatures, 0.0);

        // Make a mutable copy of the covariance matrix
        // We'll modify this copy during the deflation process
        vector<vector<double>> covarianceMatrix = originalCovarianceMatrix;

        for (int k = 0; k < numFeatures; ++k)
        {
            // Initialize a random vector for power iteration
            // The choice of initial vector can affect convergence speed, but any non-zero vector will work
            vector<double> eigenvector(numFeatures, 1.0);
            
            // Power Iteration method to find eigenvector
            // This method is simple but can be slow for finding all eigenvectors
            // More advanced methods like QR decomposition are faster for a complete eigendecomposition
            for (int iteration = 0; iteration < 1000; ++iteration)
            {
                vector<double> newEigenvector(numFeatures, 0.0);
                
                // Matrix-vector multiplication: Av
                // This operation "stretches" the vector along the direction of the dominant eigenvector
                for (int i = 0; i < numFeatures; ++i)
                {
                    for (int j = 0; j < numFeatures; ++j)
                    {
                        newEigenvector[i] += covarianceMatrix[i][j] * eigenvector[j];
                    }
                }
                
                // Normalize the resulting vector
                // Normalization prevents numerical overflow and keeps the vector pointing in the right direction
                double norm = 0.0;
                for (int i = 0; i < numFeatures; ++i)
                {
                    norm += newEigenvector[i] * newEigenvector[i];
                }
                norm = sqrt(norm);  // L2 norm
                for (int i = 0; i < numFeatures; ++i)
                {
                    eigenvector[i] = newEigenvector[i] / norm;
                }
            }
            eigenvectors[k] = eigenvector;

            // Compute eigenvalue using Rayleigh quotient: λ = (v^T * A * v) / (v^T * v)
            // The Rayleigh quotient gives us the scale factor by which the eigenvector is stretched
            // It represents the amount of variance captured by this principal component
            double eigenvalue = 0.0;
            for (int i = 0; i < numFeatures; ++i)
            {
                for (int j = 0; j < numFeatures; ++j)
                {
                    eigenvalue += eigenvector[i] * covarianceMatrix[i][j] * eigenvector[j];
                }
            }
            eigenvalues[k] = eigenvalue;

            // Deflate the matrix: A = A - λvv^T
            // Deflation removes the contribution of the found eigenvector from the matrix
            // This allows us to find the next eigenvector in the next iteration
            // Note: Accumulation of numerical errors can make later eigenvectors less accurate
            for (int i = 0; i < numFeatures; ++i)
            {
                for (int j = 0; j < numFeatures; ++j)
                {
                    covarianceMatrix[i][j] -= eigenvalue * eigenvector[i] * eigenvector[j];
                }
            }
        }

        return {eigenvalues, eigenvectors};
    }

    void sortEigenvectors(vector<double>& eigenvalues, vector<vector<double>>& eigenvectors)
    {
        // Pair eigenvalues with their corresponding eigenvectors
        // This allows us to sort both simultaneously
        vector<pair<double, vector<double>>> eigenPairs;
        for (int i = 0; i < eigenvalues.size(); ++i)
        {
            eigenPairs.emplace_back(eigenvalues[i], eigenvectors[i]);
        }

        // Sort pairs in descending order of eigenvalues
        // This gives us the principal components in order of importance (amount of variance explained)
        sort(eigenPairs.begin(), eigenPairs.end(), 
             [](const auto& a, const auto& b) { return a.first > b.first; });

        // Separate sorted eigenvalues and eigenvectors
        for (int i = 0; i < eigenPairs.size(); ++i)
        {
            eigenvalues[i] = eigenPairs[i].first;
            eigenvectors[i] = eigenPairs[i].second;
        }
    }

    vector<vector<double>> selectTopComponents(const vector<vector<double>>& eigenvectors)
    {
        // Select the first 'numComponents' eigenvectors
        // These top components capture the most significant patterns in the data
        // The number of components to keep is a trade-off between dimensionality reduction and information retention
        vector<vector<double>> topComponents(numComponents, vector<double>(eigenvectors[0].size()));
        for (int i = 0; i < numComponents; ++i)
        {
            topComponents[i] = eigenvectors[i];
        }
        return topComponents;
    }

public:
    PCA(int components) : numComponents(components) {}

    void performPCA(const vector<vector<double>>& inputData)
    {
        if (inputData.empty() || inputData[0].empty())
        {
            throw invalid_argument("Input data is empty");
        }

        // Step 1: Center the data
        // Centering is crucial for PCA to work correctly
        vector<vector<double>> centeredData = centerData(inputData);
        
        // Step 2: Compute the covariance matrix
        // The covariance matrix captures the linear relationships between all pairs of features
        vector<vector<double>> covarianceMatrix = computeCovarianceMatrix(centeredData);
        
        // Step 3: Compute eigenvectors and eigenvalues
        // Eigenvectors are the principal components, eigenvalues indicate their importance
        auto [eigenvalues, eigenvectors] = computeEigenvectors(covarianceMatrix);
        
        // Step 4: Sort eigenvectors by descending eigenvalues
        // This ensures we keep the most important components
        sortEigenvectors(eigenvalues, eigenvectors);
        
        // Step 5: Select the top components
        // These components form a new basis for our reduced-dimensional space
        principalComponents = selectTopComponents(eigenvectors);
    }

    vector<double> projectData(const vector<double>& dataPoint)
    {
        if (dataPoint.size() != principalComponents[0].size())
        {
            throw invalid_argument("Data point dimension does not match PCA dimensions");
        }

        vector<double> projectedPoint(numComponents, 0.0);
        // Project data point onto each principal component
        // This transforms the data point from the original space to the PCA space
        // The resulting coordinates represent the data point's position along each principal component
        for (int i = 0; i < numComponents; ++i)
        {
            for (int j = 0; j < dataPoint.size(); ++j)
            {
                projectedPoint[i] += dataPoint[j] * principalComponents[i][j];  // Dot product
            }
        }
        return projectedPoint;
    }

    int getNumComponents() const
    {
        return numComponents;
    }

    const vector<vector<double>>& getPrincipalComponents() const
    {
        return principalComponents;
    }
};

int main()
{
    // Example usage of the PCA class
    vector<vector<double>> data = {{1.0, 2.0, 3.0},
                                   {4.0, 5.0, 6.0},
                                   {7.0, 8.0, 9.0}};
    
    PCA pca(2);
    
    pca.performPCA(data);
    
    vector<double> newDataPoint = {2.0, 3.0, 4.0};
    vector<double> projectedPoint = pca.projectData(newDataPoint);

    cout << "Projected point: ";
    for (double val : projectedPoint)
    {
        cout << val << " ";
    }
    cout << endl;

    return 0;
}