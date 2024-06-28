#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <random>
#include <vector>

using namespace std;

class BlockwisePCA
{
private:
    int blockSize;
    int numComponents;
    int numBlocksX, numBlocksY;
    int frameHeight, frameWidth, numChannels;
    vector<vector<vector<double>>> principalComponentsPerBlock;
    vector<vector<double>> meanVectorsPerBlock;

    /*
     * This function extracts a block from the larger 3D frame.
     * It's crucial for the block-wise approach, allowing us to apply PCA locally.
     * This local application is based on the assumption that nearby pixels are more correlated.
     */
    vector<double> extractBlock(const vector<vector<vector<double>>>& frame, int startX, int startY)
    {
        vector<double> block(blockSize * blockSize * numChannels);
        for (int i = 0; i < blockSize; ++i)
        {
            for (int j = 0; j < blockSize; ++j)
            {
                for (int c = 0; c < numChannels; ++c)
                {
                    block[(i * blockSize + j) * numChannels + c] = frame[startY + i][startX + j][c];
                }
            }
        }
        return block;
    }

    /*
     * Computing the mean is a crucial step in PCA. It allows us to center the data,
     * which is necessary for computing the covariance matrix correctly.
     *
     * The mean μ for each dimension j is computed as:
     * μⱼ = (1/N) * Σᵢ xᵢⱼ
     * where N is the number of samples and xᵢⱼ is the j-th feature of the i-th sample.
     */
    vector<double> computeMean(const vector<vector<double>>& data)
    {
        int numFeatures = data[0].size();
        vector<double> mean(numFeatures, 0.0);
        for (const auto& sample : data)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                mean[j] += sample[j];
            }
        }
        for (double& m : mean)
        {
            m /= data.size();
        }
        return mean;
    }

    /*
     * The covariance matrix is central to PCA. It captures the pairwise correlations
     * between all dimensions in our data.
     *
     * For centered data, the covariance matrix C is computed as:
     * C = (1/(N-1)) * X^T * X
     * where X is the matrix of centered data (each row is a sample, each column a feature),
     * and N is the number of samples.
     *
     * Each element C_{ij} represents the covariance between features i and j.
     */
    vector<vector<double>> computeCovarianceMatrix(const vector<vector<double>>& centeredData)
    {
        int numFeatures = centeredData[0].size();
        vector<vector<double>> cov(numFeatures, vector<double>(numFeatures, 0.0));
        for (int i = 0; i < numFeatures; ++i)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                for (const auto& sample : centeredData)
                {
                    cov[i][j] += sample[i] * sample[j];
                }
                cov[i][j] /= (centeredData.size() - 1);
            }
        }
        return cov;
    }

    /*
     * This function computes the top eigenvectors of the covariance matrix using the power iteration method.
     * These eigenvectors form the principal components of our data.
     *
     * The power iteration method works as follows:
     * 1. Start with a random vector v
     * 2. Repeatedly compute v' = Av and normalize v'
     * 3. v will converge to the eigenvector corresponding to the largest eigenvalue
     *
     * We then use deflation to find subsequent eigenvectors:
     * After finding an eigenvector v with eigenvalue λ, we update A as:
     * A = A - λvv^T
     *
     * This process is repeated to find the top K eigenvectors.
     */
    vector<vector<double>> computeEigenvectors(const vector<vector<double>>& originalCov, int numComponents)
    {
        int numFeatures = originalCov.size();
        vector<vector<double>> eigenvectors(numComponents, vector<double>(numFeatures));
        
        // Create a mutable copy of the covariance matrix
        vector<vector<double>> cov = originalCov;

        for (int k = 0; k < numComponents; ++k)
        {
            vector<double> eigenvector(numFeatures, 1.0);
            for (int iter = 0; iter < 100; ++iter)
            {
                vector<double> newEigenvector(numFeatures, 0.0);
                for (int i = 0; i < numFeatures; ++i)
                {
                    for (int j = 0; j < numFeatures; ++j)
                    {
                        newEigenvector[i] += cov[i][j] * eigenvector[j];
                    }
                }
                double norm = sqrt(inner_product(newEigenvector.begin(), newEigenvector.end(), newEigenvector.begin(), 0.0));
                for (int i = 0; i < numFeatures; ++i)
                {
                    eigenvector[i] = newEigenvector[i] / norm;
                }
            }
            eigenvectors[k] = eigenvector;

            // Compute the eigenvalue (Rayleigh quotient)
            double eigenvalue = 0.0;
            for (int i = 0; i < numFeatures; ++i)
            {
                for (int j = 0; j < numFeatures; ++j)
                {
                    eigenvalue += eigenvector[i] * cov[i][j] * eigenvector[j];
                }
            }

            // Deflate the covariance matrix
            for (int i = 0; i < numFeatures; ++i)
            {
                for (int j = 0; j < numFeatures; ++j)
                {
                    cov[i][j] -= eigenvalue * eigenvector[i] * eigenvector[j];
                }
            }
        }
        return eigenvectors;
    }

public:
    /*
     * Constructor for the BlockwisePCA class.
     * Initializes the PCA parameters and prepares the data structures for storing
     * principal components and mean vectors for each block.
     */
    BlockwisePCA(int blockSize, int numComponents, int frameHeight, int frameWidth, int numChannels)
        : blockSize(blockSize), numComponents(numComponents), 
          frameHeight(frameHeight), frameWidth(frameWidth), numChannels(numChannels)
    {
        numBlocksX = frameWidth / blockSize;
        numBlocksY = frameHeight / blockSize;
        principalComponentsPerBlock.resize(numBlocksY * numBlocksX);
        meanVectorsPerBlock.resize(numBlocksY * numBlocksX);
    }

    /*
     * This method fits the BlockwisePCA model on a set of frames.
     * It's based on the idea that similar spatial locations across frames
     * will have similar statistical properties.
     *
     * For each block location (bx, by):
     * 1. We collect data from the same block across all frames.
     * 2. We compute the mean and center the data.
     * 3. We compute the covariance matrix.
     * 4. We find the principal components (top eigenvectors of the covariance matrix).
     *
     * This approach allows us to capture the most important patterns
     * for each spatial location in our frames.
     */
    void fitFrames(const vector<vector<vector<vector<double>>>>& frames)
    {
        for (int by = 0; by < numBlocksY; ++by)
        {
            for (int bx = 0; bx < numBlocksX; ++bx)
            {
                vector<vector<double>> blockDataAcrossFrames;
                for (const auto& frame : frames)
                {
                    blockDataAcrossFrames.push_back(extractBlock(frame, bx * blockSize, by * blockSize));
                }

                int blockIndex = by * numBlocksX + bx;

                // Compute mean for this block
                meanVectorsPerBlock[blockIndex] = computeMean(blockDataAcrossFrames);

                // Center the data
                for (auto& blockData : blockDataAcrossFrames)
                {
                    for (size_t j = 0; j < blockData.size(); ++j)
                    {
                        blockData[j] -= meanVectorsPerBlock[blockIndex][j];
                    }
                }

                // Compute covariance matrix
                auto covMatrix = computeCovarianceMatrix(blockDataAcrossFrames);

                // Compute principal components
                principalComponentsPerBlock[blockIndex] = computeEigenvectors(covMatrix, numComponents);
            }
        }
    }

    /*
     * This method applies our trained BlockwisePCA model to a new frame.
     * For each block:
     * 1. We extract the block.
     * 2. We center the block by subtracting the mean.
     * 3. We project it onto the principal components learned for that block location.
     * 4. We reconstruct the block, effectively reducing its information content.
     * 5. We add back the mean to restore the original scale.
     *
     * The transformation for each block can be expressed as:
     * y = W^T · (x - μ)
     * where W is the matrix of top K eigenvectors, x is our block,
     * and μ is the mean of the training data for this block.
     *
     * The reconstruction then is:
     * x' = W · y + μ
     *
     * By keeping only K components, we're approximating x with x', reducing information.
     * This process maintains the original frame size while reducing the effective
     * dimensionality of each block.
     */
    vector<vector<vector<double>>> transformFrame(const vector<vector<vector<double>>>& frame)
    {
        vector<vector<vector<double>>> transformedFrame = frame;

        for (int by = 0; by < numBlocksY; ++by)
        {
            for (int bx = 0; bx < numBlocksX; ++bx)
            {
                auto block = extractBlock(frame, bx * blockSize, by * blockSize);

                int blockIndex = by * numBlocksX + bx;

                // Center the block
                for (size_t j = 0; j < block.size(); ++j)
                {
                    block[j] -= meanVectorsPerBlock[blockIndex][j];
                }

                // Project onto principal components
                vector<double> transformedBlock(numComponents, 0.0);
                for (int i = 0; i < numComponents; ++i)
                {
                    for (size_t j = 0; j < block.size(); ++j)
                    {
                        transformedBlock[i] += block[j] * principalComponentsPerBlock[blockIndex][i][j];
                    }
                }

                // Reconstruct the block
                vector<double> reconstructedBlock(blockSize * blockSize * numChannels, 0.0);
                for (int i = 0; i < numComponents; ++i)
                {
                    for (size_t j = 0; j < block.size(); ++j)
                    {
                        reconstructedBlock[j] += transformedBlock[i] * principalComponentsPerBlock[blockIndex][i][j];
                    }
                }

                // Add back the mean and reshape
                for (int i = 0; i < blockSize; ++i)
                {
                    for (int j = 0; j < blockSize; ++j)
                    {
                        for (int c = 0; c < numChannels; ++c)
                        {
                            int index = (i * blockSize + j) * numChannels + c;
                            transformedFrame[by * blockSize + i][bx * blockSize + j][c] =
                                reconstructedBlock[index] + meanVectorsPerBlock[blockIndex][index];
                        }
                    }
                }
            }
        }

        return transformedFrame;
    }
};