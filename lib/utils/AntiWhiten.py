"""
An implementation of data whitening based on eigenvalues of the covariance
matrix. It can be used as dimensionality reduction or as data preprocessing.
Usage is similar to that of sklearn's decomposition module (i.e. PCA).
Please note that this implementation is not at all optimized for speed or memory
usage.
"""

import numpy as np

#------------------------------------------------------------------------------#


class AntiWhiten:

    """
    Perform linear projection on data with options to manipulate covariance
    of projected data. Can also be used as dimension reduction.

    deg
    ---
     -1     : whiten (covariance matrix is identity matrix)
      0		: normal linear PCA
     >= 1 	: "anti-whiten" (covariance is mutiplied)

    Stored variables
    ----------------
    n_components : number of components to keep
    deg          : degree of whitening
    mean         : mean of data used to fit the model
    X = U * (S * sqrt(n_components)) * V.T
    S            : list of sorted singular values divided by sqrt(n_components)
    V            : projection matrix
    S and V drop dimensions if deg is specified when constructed
    """

    def __init__(self, n_components=None, deg=None):
        """
        Init function, specify n_components here if the object will be used
        only with one number of dimensions
        """

        self.n_components = n_components
        self.deg = deg

    def _check_dim(self, dim, data_len):
        """Return valid dimensions"""

        if dim is None:
            dim = self.n_components
            if dim is None:
                dim = data_len
        if isinstance(dim, (int, long)) and (dim > 0) and (dim <= len(self.V_)):
            return dim
        else:
            raise ValueError('Invalid number of dimensions.')

    def _check_deg(self, deg):
        """Return valid whiten degree"""

        if deg is None:
            deg = self.deg
            if deg is None:
                deg = 0
        if isinstance(deg, (int, long)) and (deg >= -1):
            return deg
        else:
            raise ValueError(
                'Invalid number of whitening degree (must >= -1).')

    def _svd_flip(self, u, v):
        """Sign correction to ensure deterministic output from SVD.
        Adjusts the columns of u and the rows of v such that the loadings in the
        columns in u that are largest in absolute value are always positive.
        Parameters
        ----------
        u, v : ndarray
            u and v are the output of `linalg.svd` or
            `sklearn.utils.extmath.randomized_svd`, with matching inner
            dimensions so one can compute `np.dot(u * s, v)`.
        Returns
        -------
        u_adjusted, v_adjusted : arrays with the same dimensions as the input.
        (Code taken from sklearn library)
        """

        # columns of u, rows of v
        max_abs_cols = np.argmax(np.abs(u), axis=0)
        signs = np.sign(u[max_abs_cols, xrange(u.shape[1])])
        u *= signs
        v *= signs[:, np.newaxis]
        return u, v

    def fit(self, X):
        """Fit X. Assume that X has shape (n_samples, n_features)"""

        self.n_samples = X.shape[0]
        # Center data
        self.mean_ = np.mean(X, axis=0)
        X_center = X - self.mean_

        U, S, V = np.linalg.svd(X_center, full_matrices=False)
        # Flip signs of U, V to ensure deterministic outputs
        _, V = self._svd_flip(U, V)
        self.V_ = V.T
        self.S_ = S / np.sqrt(self.n_samples)

        # Keep only the first <n_components> if specified
        if self.n_components is not None:
            self.V_ = self.V_[:, :self.n_components]
            self.S_ = self.S_[:self.n_components]

    def transform(self, X, deg=None, dim=None):
        """Transform X"""

        # TODO: check if fit has been called

        # Center data
        X_center = X - self.mean_

        # If <n_components> was specified, use S, V directly; otherwise, keep
        # first <dim> components
        if self.n_components is not None:
            S = np.diag(self.S_)
            V = self.V_
        else:
            dim = self._check_dim(dim, X.shape[1])
            S = np.diag(self.S_[:dim])
            V = self.V_[:, :dim]

        X_pca = np.dot(X_center, V)
        deg = self._check_deg(deg)
        if deg == -1:
            # X_whiten = X * V / S * sqrt(n_samples) = U * sqrt(n_samples)
            S_inv = np.diag(1 / self.S_)
            X_proj = np.dot(X_pca, S_inv)
        elif deg == 0:
            # X_pca = X * V = U * S * V^T * V = U * S
            X_proj = X_pca
        elif deg >= 1:
            # X_antiwhite = X * V * (S / sqrt(n_samples))^deg
            X_proj = X_pca
            for i in range(deg):
                X_proj = np.dot(X_proj, S)

        return X_proj

    def inverse_transform(self, X, deg=None, inv_option=1):
        """
        Inverse transform projects X back to its original space based on
        inv_option:
        1 : multiplying with both S and components matrix corresponding to
            degree of antiwhitening
        2 : only multiplying with transpose of components matrix regardless of
            degree of antiwhitening
        """

        # If <n_components> was specified, use S, V directly; otherwise, keep
        # first <dim> components
        if self.n_components is not None:
            S = np.diag(self.S_)
            V = self.V_
        else:
            dim = self._check_dim(dim, X.shape[1])
            S = np.diag(self.S_[:dim])
            V = self.V_[:, :dim]

        if inv_option == 1:
            deg = self._check_deg(deg)
            if deg == -1:
                # X_whiten = X * V / S * sqrt(n_samples)
                temp = np.dot(X, S)
                X_inv = np.dot(temp, V.T)
            elif deg == 0:
                # X_pca = X * V
                X_inv = np.dot(X, V.T)
            elif deg >= 1:
                # X_antiwhite = X * V * (S / sqrt(n_samples))^deg
                temp = X
                for i in range(deg):
                    temp = np.dot(temp, np.linalg.inv(S))
                X_inv = np.dot(temp, V.T)

        elif inv_option == 2:
            X_inv = np.dot(X, V.T)

        return X_inv + self.mean_
