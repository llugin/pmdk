// SPDX-License-Identifier: BSD-3-Clause
/* Copyright 2018-2020, Intel Corporation */

/*
 * badblocks_none.c -- fake bad blocks functions
 */

#include <errno.h>

#include "out.h"
#include "badblocks.h"

/*
 * badblocks_devdax_clear_badblocks_all -- fake bad block clearing routine
 */
int
badblocks_devdax_clear_badblocks_all(const char *path)
{
	LOG(3, "path %s", path);

	return 0;
}

/*
 * badblocks_count -- returns number of bad blocks in the file
 *                       or -1 in case of an error
 */
long
badblocks_count(const char *file)
{
	LOG(3, "file %s", file);

	/* not supported */
	errno = ENOTSUP;
	return -1;
}

/*
 * badblocks_get -- returns list of bad blocks in the file
 */
int
badblocks_get(const char *file, struct badblocks *bbs)
{
	LOG(3, "file %s", file);

	/* not supported */
	errno = ENOTSUP;
	return -1;
}

/*
 * badblocks_clear -- clears the given bad blocks in a file
 *                       (regular file or dax device)
 */
int
badblocks_clear(const char *file, struct badblocks *bbs)
{
	LOG(3, "file %s badblocks %p", file, bbs);

	/* not supported */
	errno = ENOTSUP;
	return -1;
}

/*
 * badblocks_clear_all -- clears all bad blocks in a file
 *                           (regular file or dax device)
 */
int
badblocks_clear_all(const char *file)
{
	LOG(3, "file %s", file);

	/* not supported */
	errno = ENOTSUP;
	return -1;
}
