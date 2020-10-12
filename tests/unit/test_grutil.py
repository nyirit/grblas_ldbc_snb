from grblas.matrix import Matrix

from ldbc_snb_grblas.grutil import merge_matrix


def test_merge_matrix_col_wise():
    a = Matrix.from_values(
        [0, 0, 1, 2, 1],
        [0, 1, 2, 1, 3],
        [1, 2, 3, 4, 5],
    )
    b = Matrix.from_values(
        [0, 2],
        [0, 1],
        [6, 7]
    )
    expected_result = Matrix.from_values(
        [0, 0, 1, 2, 1, 0, 2],
        [0, 1, 2, 1, 3, 4, 5],
        [1, 2, 3, 4, 5, 6, 7],
    )

    result = merge_matrix(a, b, row_wise=False, create_new=True)

    assert id(result) != id(a)  # 'result' and 'a' should be different objects
    assert result.isequal(expected_result)

    result = merge_matrix(a, b, row_wise=False, create_new=False)
    assert id(result) == id(a)  # 'result' and 'a' should be the same object
    assert result.isequal(expected_result)


def test_merge_matrix_row_wise():
    a = Matrix.from_values(
        [0, 0, 1, 2, 1],
        [0, 1, 2, 1, 3],
        [1, 2, 3, 4, 5],
    )
    b = Matrix.from_values(
        [0, 1],
        [0, 3],
        [6, 7]
    )
    expected_result = Matrix.from_values(
        [0, 0, 1, 2, 1, 3, 4],
        [0, 1, 2, 1, 3, 0, 3],
        [1, 2, 3, 4, 5, 6, 7],
    )

    result = merge_matrix(a, b, row_wise=True, create_new=True)

    assert id(result) != id(a)  # 'result' and 'a' should be different objects
    assert result.isequal(expected_result)

    result = merge_matrix(a, b, row_wise=True, create_new=False)
    assert id(result) == id(a)  # 'result' and 'a' should be the same object
    assert result.isequal(expected_result)
