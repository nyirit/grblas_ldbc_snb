from grblas.matrix import Matrix


def merge_matrix(a: Matrix, b: Matrix, *, create_new=False, row_wise=True):
    """
    Creates a matrix using matrices 'a' and 'b'. If 'create_new' is false, 'a' will be overwritten,
    otherwise a new matrix will be created.

    :param a:
    :param b:
    :param create_new:
    :param row_wise: if True 'b' matrix will be added as rows to 'a', otherwise as columns.
    :return:
    """

    result = a.dup() if create_new else a

    if row_wise:
        if a.ncols != b.ncols:
            raise ValueError(f"Row-wise merge is not possible as a.ncols != b.ncols. "
                             f"{a.ncols} != {b.ncols}")

        a_nrows = a.nrows

        result.resize(a.nrows + b.nrows, a.ncols)
        result[a_nrows:a_nrows+b.nrows, :] = b

    else:
        if a.nrows != b.nrows:
            raise ValueError(f"Row-wise merge is not possible as a.nrows != b.nrows. "
                             f"{a.nrows} != {b.nrows}")

        a_ncols = a.ncols

        result.resize(a.nrows, a.ncols + b.ncols)
        result[:, a_ncols:a_ncols + b.ncols] = b

    return result
