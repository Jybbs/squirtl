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
    vector<vector<vector<double>>> principalComponentsPerBlock;
    vector<vector<double>> meanVectorsPerBlock;

    // Extract a block from a frame
    vector<vector<double>> extractBlock(const vector<vector<double>> &frame, int startX, int startY)
    {
        /*
        This function extracts a square block from the larger frame.
        It's crucial for the block-wise approach, allowing us to apply PCA locally.
        This local application is based on the assumption that nearby pixels are more correlated,
        */
        vector<vector<double>> block(blockSize, vector<double>(blockSize));
        for (int i = 0; i < blockSize; ++i)
        {
            for (int j = 0; j < blockSize; ++j)
            {
                block[i][j] = frame[startY + i][startX + j];
            }
        }
        return block;
    }

    // Flatten a 2D block into a 1D vector
    vector<double> flattenBlock(const vector<vector<double>> &block)
    {
        /*
        Flattening is necessary because PCA typically operates on 1D data vectors.
        This step transforms our 2D image block into a point in a high-dimensional space.
        Each pixel becomes a dimension in this space.

        Mathematically, we're performing a reshaping operation:
        v = vec(B), where v is a vector of length blockSize²
        This operation is reversible, which is crucial for later reconstruction.
        */
        vector<double> flatBlock;
        for (const auto &row : block)
        {
            flatBlock.insert(flatBlock.end(), row.begin(), row.end());
        }
        return flatBlock;
    }

    // Compute mean of a set of vectors
    vector<double> computeMean(const vector<vector<double>> &data)
    {
        /*
        Computing the mean is a crucial step in PCA. It allows us to center the data,
        which is necessary for computing the covariance matrix correctly.

        The mean μ for each dimension j is computed as:
        μⱼ = (1/N) * Σᵢ xᵢⱼ
        where N is the number of samples and xᵢⱼ is the j-th feature of the i-th sample.
        */
        int numFeatures = data[0].size();
        vector<double> mean(numFeatures, 0.0);
        for (const auto &sample : data)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                mean[j] += sample[j];
            }
        }
        for (double &m : mean)
        {
            m /= data.size();
        }
        return mean;
    }

    // Compute covariance matrix
    vector<vector<double>> computeCovarianceMatrix(const vector<vector<double>> &centeredData)
    {
        /*
        The covariance matrix is central to PCA. It captures the pairwise correlations
        between all dimensions in our data.

        For centered data, the covariance matrix C is computed as:
        C = (1/(N-1)) * X^T * X
        where X is the matrix of centered data (each row is a sample, each column a feature),
        and N is the number of samples.

        Each element C_{ij} represents the covariance between features i and j.
        */
        int numFeatures = centeredData[0].size();
        vector<vector<double>> cov(numFeatures, vector<double>(numFeatures, 0.0));
        for (int i = 0; i < numFeatures; ++i)
        {
            for (int j = 0; j < numFeatures; ++j)
            {
                for (const auto &sample : centeredData)
                {
                    cov[i][j] += sample[i] * sample[j];
                }
                cov[i][j] /= (centeredData.size() - 1);
            }
        }
        return cov;
    }

    vector<vector<double>> computeEigenvectors(const vector<vector<double>>& originalCov, int numComponents)
    {
        /*
        This function computes the top eigenvectors of the covariance matrix using the power iteration method.
        These eigenvectors form the principal components of our data.

        The power iteration method works as follows:
        1. Start with a random vector v
        2. Repeatedly compute v' = Av and normalize v'
        3. v will converge to the eigenvector corresponding to the largest eigenvalue

        We then use deflation to find subsequent eigenvectors:
        After finding an eigenvector v with eigenvalue λ, we update A as:
        A = A - λvv^T

        This process is repeated to find the top K eigenvectors.
        */
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
    BlockwisePCA(int blockSize, int numComponents, int frameHeight, int frameWidth)
        : blockSize(blockSize), numComponents(numComponents)
    {
        numBlocksX = frameWidth / blockSize;
        numBlocksY = frameHeight / blockSize;
        principalComponentsPerBlock.resize(numBlocksX * numBlocksY);
        meanVectorsPerBlock.resize(numBlocksX * numBlocksY);
    }

    void fitFrames(const vector<vector<vector<double>>> &frames)
    {
        /*
        This method trains our BlockwisePCA model on a set of frames.
        It's based on the idea that similar spatial locations across frames
        will have similar statistical properties.

        For each block location (bx, by):
        1. We collect data from the same block across all frames.
        2. We compute the mean and center the data.
        3. We compute the covariance matrix.
        4. We find the principal components (top eigenvectors of the covariance matrix).

        This approach allows us to capture the most important patterns
        for each spatial location in our frames.

        Foreach block, we find the eigenvectors of the covariance matrix:
        C = (1/M) Σ(xᵢ · xᵢᵀ) for i = 1 to M, where M is the number of frames
        and xᵢ are the flattened blocks from each frame.
        */
        for (int by = 0; by < numBlocksY; ++by)
        {
            for (int bx = 0; bx < numBlocksX; ++bx)
            {
                vector<vector<double>> blockDataAcrossFrames;
                for (const auto &frame : frames)
                {
                    auto block = extractBlock(frame, bx * blockSize, by * blockSize);
                    blockDataAcrossFrames.push_back(flattenBlock(block));
                }

                int blockIndex = by * numBlocksX + bx;

                // Compute mean for this block
                meanVectorsPerBlock[blockIndex] = computeMean(blockDataAcrossFrames);

                // Center the data
                for (auto &blockData : blockDataAcrossFrames)
                {
                    for (int j = 0; j < blockData.size(); ++j)
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

    vector<vector<double>> transformFrame(const vector<vector<double>> &frame)
    {
        /*
        This method applies our trained BlockwisePCA model to a new frame.
        For each block:
        1. We extract and flatten the block.
        2. We center the block by subtracting the mean.
        3. We project it onto the principal components learned for that block location.
        4. We reconstruct the block, effectively reducing its information content.
        5. We add back the mean to restore the original scale.

        The transformation for each block can be expressed as:
        y = Wᵀ · (x - μ)
        where W is the matrix of top K eigenvectors, x is our flattened block,
        and μ is the mean of the training data for this block.

        The reconstruction then is:
        x' = W · y + μ

        By keeping only K components, we're approximating x with x', reducing information.
        This process maintains the original frame size while reducing the effective
        dimensionality of each block.
        */
        vector<vector<double>> transformedFrame = frame; // Start with a copy of the original frame

        for (int by = 0; by < numBlocksY; ++by)
        {
            for (int bx = 0; bx < numBlocksX; ++bx)
            {
                auto block = extractBlock(frame, bx * blockSize, by * blockSize);
                auto flatBlock = flattenBlock(block);

                int blockIndex = by * numBlocksX + bx;

                // Center the block
                for (int j = 0; j < flatBlock.size(); ++j)
                {
                    flatBlock[j] -= meanVectorsPerBlock[blockIndex][j];
                }

                // Project onto principal components
                vector<double> transformedBlock(numComponents, 0.0);
                for (int i = 0; i < numComponents; ++i)
                {
                    for (int j = 0; j < flatBlock.size(); ++j)
                    {
                        transformedBlock[i] += flatBlock[j] * principalComponentsPerBlock[blockIndex][i][j];
                    }
                }

                // Reconstruct the block
                vector<double> reconstructedBlock(blockSize * blockSize, 0.0);
                for (int i = 0; i < numComponents; ++i)
                {
                    for (int j = 0; j < flatBlock.size(); ++j)
                    {
                        reconstructedBlock[j] += transformedBlock[i] * principalComponentsPerBlock[blockIndex][i][j];
                    }
                }

                // Add back the mean and reshape
                for (int i = 0; i < blockSize; ++i)
                {
                    for (int j = 0; j < blockSize; ++j)
                    {
                        int index = i * blockSize + j;
                        transformedFrame[by * blockSize + i][bx * blockSize + j] =
                            reconstructedBlock[index] + meanVectorsPerBlock[blockIndex][index];
                    }
                }
            }
        }

        return transformedFrame;
    }
};

int main()
{
    const int frameHeight = 144;
    const int frameWidth = 160;
    const int blockSize = 16;
    const int numComponents = 5;
    const int numFrames = 100;

    BlockwisePCA bpca(blockSize, numComponents, frameHeight, frameWidth);

    // Set up random number generation
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    std::default_random_engine generator(seed);
    std::uniform_int_distribution<int> distribution(0, 255);

    // Generate random frame data for demonstration
    std::vector<std::vector<std::vector<double>>> frames;
    for (int f = 0; f < numFrames; ++f)
    {
        std::vector<std::vector<double>> frame(frameHeight, std::vector<double>(frameWidth));
        for (int i = 0; i < frameHeight; ++i)
        {
            for (int j = 0; j < frameWidth; ++j)
            {
                frame[i][j] = static_cast<double>(distribution(generator));
            }
        }
        frames.push_back(frame);
    }

    std::cout << "Fitting BlockwisePCA model..." << std::endl;
    bpca.fitFrames(frames);

    std::cout << "Transforming a new frame..." << std::endl;
    std::vector<std::vector<double>> newFrame(frameHeight, std::vector<double>(frameWidth));
    for (int i = 0; i < frameHeight; ++i)
    {
        for (int j = 0; j < frameWidth; ++j)
        {
            newFrame[i][j] = static_cast<double>(distribution(generator));
        }
    }

    auto transformedFrame = bpca.transformFrame(newFrame);

    std::cout << "Original frame size: " << frameHeight << "x" << frameWidth << std::endl;
    std::cout << "Transformed frame size: " << transformedFrame.size() << "x" << transformedFrame[0].size() << std::endl;
    std::cout << "Number of blocks: " << (frameHeight / blockSize) * (frameWidth / blockSize) << std::endl;
    std::cout << "Components retained per block: " << numComponents << std::endl;

    return 0;
}