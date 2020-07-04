import numpy as np
import scipy.linalg as sp


def int_to_binary(n):
    """Converts an integer :math:`n` to a size-:math:`\\log_2(n)` binary array.

    :param n: Integer to convert
    :type n: int
    :return: Binary array representing :math:`n`.
    """
    assert n >= 0
    return np.array([np.array(list(np.binary_repr(n)), dtype=int)])


def binary_to_int(b):
    """Converts a size-:math:`\\log_2(n)` binary array :math:`b` to an integer.

    :param b: Binary array representing :math:`n`
    :type b: np.array
    :return: Integer :math:`n` represented by :math:`b`.
    """
    return int(b.dot(2 ** np.arange(b.size)[::-1]))


def tensor_product(A):
    """
    :param A: List of numpy arrays to tensor product together
    :type A: list
    :return: Full tensor product of tensors all numpy arrays listed in :math:`A`.
    """
    a = 1
    for i in A:
        a = np.kron(a, i)
    return a


def outer_product(a, b):
    """
    :param a: First numpy array to use in the outer product, should be of the form :math:`|a\\rangle` and have dimension :math:`(k, 1)`
    :type a: np.array
    :param b: Second  numpy array to use in the outer product, should be of the form :math:`|b\\rangle` and have dimension :math:`(k, 1)`
    :type b: np.array
    :return: Outer product :math:`| a\\rangle\\langle b|`
    """
    return a @ b.conj().T


def X(n=1):
    """
    :return: Returns :math:`X^{\\otimes n}`
    """
    x = [np.array([[0, 1], [1, 0]], dtype=np.complex128)] * n
    return tensor_product(x)


def Y(n=1):
    """
    :return: Returns :math:`Y^{\\otimes n}`
    """
    y = [np.array([[0, -1j], [1j, 0]], dtype=np.complex128)] * n
    return tensor_product(y)


def Z(n=1):
    """
    :return: Returns :math:`Z^{\\otimes n}`
    """
    z = [np.array([[1, 0], [0, -1]], dtype=np.complex128)] * n
    return tensor_product(z)


def hadamard(n=1):
    """
    :return: Returns :math:`\\frac{1}{2^{n/2}}(|0\\rangle+|1\\rangle)^{\\otimes n}`
    """
    h = [np.array([[1, 1], [1, -1]]) / np.sqrt(2)] * n
    return tensor_product(h)


def identity(n=1, d=2):
    """Base :math:`d` identity matrix.

    :return: Returns :math:`\\mathbf{1}^{d^n\\times  d^n}`
    """
    return np.identity(d ** n)


def trace(a, ind=None, d=2):
    """
    Performs a partial trace over the matrix :math:`a`.

    :param a: Operator to perform a partial trace over.
    :type a: np.array
    :param ind: List of qudit indices to perform the partial trace over. If None, all indices will be traced over.
    :type ind: list
    :param d: Dimension of the qudit, defaults to two for qubits.
    :type d: int
    :return: The result of the partial trace. When all indices are traced over, a float is returned; otherwise a numpy array is returned.
    """
    # Operator a and basis b
    # If ind is None, trace over all indices
    if ind is None:
        return np.trace(a)
    # Put indices in reverse order
    ind = list(ind)
    ind.sort(reverse=True)
    # Partial trace
    for k in ind:
        N = int(np.log2(a.shape[-1]))
        a = np.reshape(a, [d ** (N - k - 1), d ** (k + 1), d ** N], order='C')
        a[:, d ** k:d ** (k + 1), :] = np.roll(a[:, d ** k:d ** (k + 1), :], shift=-2 ** k, axis=2)
        a = np.reshape(a, [d ** (2 * N - k - 1), d, d ** k], order='C')
        a = np.delete(a, obj=1, axis=1)
        a = np.reshape(a, [d ** (2 * N - 2 - 2 * k), d, d ** (2 * k)], order='C')
        a = np.sum(a, axis=1)
        a = np.reshape(a, [d ** (N - 1), d ** (N - 1)], order='C')
    return np.trace(a)


def is_orthonormal(B):
    """
    Given a basis :math:`B` of shape :math:`(n, n, 1)` comprised of :math:`n` shape-:math:`(n, 1)` basis vectors,
    check if it is orthonormal.

    :param B: Basis to check.
    :type A: np.array
    :return: ``True`` if and only if all basis vectors are orthonormal
    """
    return np.array_equal(np.linalg.inv(B) @ B, np.identity(B.shape[-1]))


def equal_superposition(N: int, basis=np.array([[[1], [0]], [[0], [1]]]), dtype=np.complex128):
    """
    :param N:  N is the number of logical qubits.
    :type N: int
    :param basis: Basis is an array of dimension :math:`(2, 2^n, 1)` containing the two basis states of the code comprised of :math:`n` qubits.
    :return: An equal superposition of logical basis states, :math:`\\frac{1}{2^{N/2}}(|0_L\\rangle+|1_L\\rangle)^{\\otimes N}`.
    """
    plus = (basis[0] + basis[1])
    return tensor_product([plus] * N) / np.sqrt(2 ** N).astype(dtype)


def multiply(state, operator, is_ket=False):
    # Multiplies a state by an operator
    if is_ket:
        return operator @ state
    else:
        return operator @ state @ operator.conj().T


def commutator(A, B):
    """
    :return: The commutator of :math:`A` and :math:`B`, given by :math:`[A, B]=AB-BA`.
    """
    return A @ B - B @ A


def anticommutator(A, B):
    """
    :return: The anticommutator of :math:`A` and :math:`B`, given by :math:`\\{A, B\\}=AB+BA`.
    """
    return A @ B + B @ A


def is_hermitian(H):
    """
    :param H: Operator to check if Hermitian
    :type H: np.array
    :return: ``True`` if and only if :math:`H^\\dagger = H`.
    """
    return np.allclose(H, H.conj().T)


def trace_norm(A, B):
    """
    :return:  The trace norm between density operators :math:`A` and :math:`B`, given by :math:`\\text{tr}(A-B)`. Note this measure of fidelity is only valid for pure states, not mixed states.
    """
    return np.trace(A - B, axis1=1, axis2=2)


def fidelity(A, B):
    """
    :return:  The fidelity between density matrices :math:`A` and :math:`B`, given by :math:`\\text{tr}(\\sqrt{\\sqrt{A}B\\sqrt{A}})`.
    """
    return np.trace(sp.sqrtm(sp.sqrtm(A) @ B @ sp.sqrtm(A))) ** 2


def is_projector(A):
    """
    :param A: Operator to check if it is a projector
    :type A: np.array
    :return: ``True`` if and only if :math:`A^2 = A`
    """
    return np.allclose(A, A @ A)


def is_involutary(A):
    """
    :param A: Operator to check if it is involutary
    :type A: np.array
    :return: ``True`` if and only if :math:`A^2 = \\mathbf{1}`
    """
    return np.allclose(A @ A, np.identity(A.shape[0]))


def is_pure_state(state):
    """Returns ``True`` if :py:attr:`state` is a pure state."""
    return np.array_equal(state @ state, state)


def is_valid_state(state, is_ket=False, verbose=True):
    """Returns ``True`` if :py:attr:`state` is a valid density matrix or a ket."""
    if is_ket:
        return np.linalg.norm(state) == 1
    else:
        print('Eigenvalues real?', (np.allclose(np.imag(np.linalg.eigvals(state)), np.zeros(state.shape[0]))))
        print('Eigenvalues positive?', np.all(np.real(np.linalg.eigvals(state)) >= -1e-10))
        print('Trace 1?', np.isclose(np.absolute(np.trace(state)), 1))
        if verbose:
            print('Eigenvalues:', np.linalg.eigvals(state))
            print('Trace:', np.trace(state))
        return (np.allclose(np.imag(np.linalg.eigvals(state)), np.zeros(state.shape[0]), atol=1e-06) and
                np.all(np.real(np.linalg.eigvals(state)) >= -1 * 1e-7) and
                np.isclose(np.absolute(np.trace(state)), 1))


def is_diagonal(A):
    """Checks if a matrix :math:`A` is diagonal."""
    if np.count_nonzero(A - np.diag(np.diagonal(A))) == 0:
        return True
    return False


def is_sorted(A, unique=True):
    """Returns True if and only if A is a sorted list or numpy array. """
    for i in range(len(A) - 1):
        if unique:
            if A[i + 1] < A[i]:
                return False
        else:
            if A[i + 1] <= A[i]:
                return False
    return True


def is_ket(A):
    """Return True if and only if A is a ket and not a density matrix."""
    assert len(A.shape) == 2
    if A.shape[-1] == 1:
        return True
    else:
        assert A.shape[0] == A.shape[1]
        return False


def is_pure(A):
    """Return True if and only if A is a pure state or ket."""
    if is_ket(A):
        return True
    if np.isclose(np.trace(A @ A), 1):
        return True
    return False


def purity(A):
    if not is_ket(A):
        return np.trace(A @ A)
    else:
        return 1
