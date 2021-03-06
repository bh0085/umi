from __future__ import print_function
import os
import re
import gzip
import itertools
import argparse
import time
import logging

from multiprocessing import Pool, Value, Array

import multiglobals # anything (empty .py file)
multiglobals.read1 = ""
multiglobals.read2 = ""
multiglobals.index1 = ""
multiglobals.index2 = ""
multiglobals.stride = ""
multiglobals.samplenames = []
multiglobals.max_count = ""

__author__ = 'Martin Aryee'

logger = logging.getLogger('root')

#args = {'out_dir':'/PHShome/ma695/tmp', 'min_reads':10}
#base = '/data/joung/sequencing_bcl/131007_M01326_0075_000000000-A6B33/Data/Intensities/BaseCalls'
#args['read1'] = os.path.join(base, 'Undetermined_S0_L001_R1_001.fastq.gz')
#args['read2'] = os.path.join(base, 'Undetermined_S0_L001_R2_001.fastq.gz')
#args['index1'] = os.path.join(base, 'Undetermined_S0_L001_I1_001.fastq.gz')
#args['index2'] = os.path.join(base, 'Undetermined_S0_L001_I2_001.fastq.gz')

def split_file(fname,lines_per_file):
    count = 0
    file_count = 0
    buffer=[]
    with open(fname) as fopen:
        while True:
            l = fopen.readline()
            if not l: break
            buffer += [l]
            if len(buffer) == lines_per_file:
                with open(fname+".split.{0}.{1}".format(lines_per_file,file_count),"w") as subf_open:
                    subf_open.write("\n".join(buffer))
                    file_count+=1
                    buffer=[]
            count+=1

def fq(file, start=0, max_count=-1):
    count=0
    if re.search('.gz$', file):
        fastq = gzip.open(file, 'rb')
    else:
        fastq = open(file, 'r')
    with fastq as f:
        #if start>0:
        #    junk = f.readlines(4*start)


        #        logger.info('Read %d into junk!',start_record)

        while True:
            if count <start:
                f.readline()
                f.readline()
                f.readline()
                f.readline()
                count+=1
                continue

            count+=1
            if max_count >=0 and count >max_count: break

            l1 = f.readline()
            if not l1:
                break
            l2 = f.readline()
            l3 = f.readline()
            l4 = f.readline()
            yield [l1, l2, l3, l4]


def get_sample_id(i1, i2, sample_names):
    seq1 = i1[1]
    seq2 = i2[1]
    sample_barcode = seq1[1:8] + seq2[1:8]
    if sample_barcode in sample_names:
        return sample_names[sample_barcode]
    else:
        return sample_barcode


def read_core(start_record):
        #return [1,2,3,4]



        stride=multiglobals.stride



        r1s = list(fq("".join(multiglobals.read1),start=start_record,max_count=stride+start_record))
        r2s = list(fq("".join(multiglobals.read2),start=start_record,max_count=stride+start_record))
        i1s = list(fq("".join(multiglobals.index1),start=start_record,max_count=stride+start_record))
        i2s = list(fq("".join(multiglobals.index2),start=start_record,max_count=stride+start_record))

        logger.info('Time passed is %d ', time.time() - multiglobals.starttime)


        ids = [get_sample_id(i1s[idx],i2s[idx],multiglobals.sample_names) for idx in range(0,stride)]

        keys = set(ids)
        r1_map = dict([(k,[]) for k in keys])
        r2_map = dict([(k,[]) for k in keys])
        i1_map = dict([(k,[]) for k in keys])
        i2_map = dict([(k,[]) for k in keys])

        #logger.info('keys are {0}'.format(" ".join(list(keys))))


        for i,e in enumerate(ids):
            r1_map[ids[i]] = r1s[i]
            r2_map[ids[i]] = r2s[i]
            i1_map[ids[i]] = i1s[i]
            i2_map[ids[i]] = i2s[i]


        return [r1_map, r2_map, i1_map, i2_map]


def demultiplex(read1, read2, index1, index2, sample_barcodes, out_dir, min_reads=10000):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if type(sample_barcodes) != dict:
        sample_names = {}
        if not sample_barcodes==None:
            for line in open(sample_barcodes, 'r'):
                fields = line.strip().split('\t')
                if len(fields)==2:
                    sampleid, barcode = fields
                    sample_names[barcode] = sampleid
    else:
        sample_names = sample_barcodes

    outfiles_r1 = {}
    outfiles_r2 = {}
    outfiles_i1 = {}
    outfiles_i2 = {}

    total_count = 0
    count = {}
    buffer_r1 = {}
    buffer_r2 = {}
    buffer_i1 = {}
    buffer_i2 = {}

    #it = itertools.izip(fq(args['read1']), fq(args['read2']), fq(args['index1']), fq(args['index2']))
    #for r1,r2,i1,i2 in itertools.islice(it, 0, 100):
    start = time.time()

    cores = 40
    stride = 1000000
    total_count = 0

    all_r1s = {}
    all_r2s = {}
    all_i1s = {}
    all_i2s = {}

    multiglobals.starttime=start
    multiglobals.read1=read1
    multiglobals.read2=read2
    multiglobals.index1=index1
    multiglobals.index2=index2
    multiglobals.sample_names = sample_names
    multiglobals.stride=stride
    multiglobals.total_count=total_count

    from contextlib import closing


    for fname in [read1,read2,index1,index2]:
        split_file(fname,stride * 4)
    raise Exception()

    with closing(Pool(processes=cores)) as p:
        #params = [i*stride for i in range(cores*10)]
        #logger.info('PARAMETERS {0}'.format(params))
        outs = p.map(read_core, [i*stride for i in range(cores)*5])

        p.terminate()
    logger.info('Pool yielded %d results from %d cores', len(outs), cores)

    for out in outs:
        if out == None: break
        else: total_count += len(out[0])
        for k in out[0].keys():
            all_r1s[k]=all_r1s.get(k,[])+out[0][k]
            all_r2s[k]=all_r2s.get(k,[])+out[1][k]
            all_i1s[k]=all_i1s.get(k,[])+out[2][k]
            all_i2s[k]=all_i2s.get(k,[])+out[3][k]

    for sample_id in all_r1s.keys():
        if len(all_r1s[sample_id]) >= min_reads:
            outfiles_r1[sample_id] = open(os.path.join(out_dir, '%s.r1.fastq' % sample_id), 'w')
            outfiles_r2[sample_id] = open(os.path.join(out_dir, '%s.r2.fastq' % sample_id), 'w')
            outfiles_i1[sample_id] = open(os.path.join(out_dir, '%s.i1.fastq' % sample_id), 'w')
            outfiles_i2[sample_id] = open(os.path.join(out_dir, '%s.i2.fastq' % sample_id), 'w')

            # Spill the buffers to sample-specific fastqs
            for record in all_r1s[sample_id]:
                outfiles_r1[sample_id].write(''.join(record))
            for record in all_r2s[sample_id]:
                outfiles_r2[sample_id].write(''.join(record))
            for record in all_i1s[sample_id]:
                outfiles_i1[sample_id].write(''.join(record))
            for record in all_i2s[sample_id]:
                outfiles_i2[sample_id].write(''.join(record))

            del all_r1s[sample_id]
            del all_r2s[sample_id]
            del all_i1s[sample_id]
            del all_i2s[sample_id]

    # Write remaining buffered reads to a single fastq.
    # (These reads correspond to barcodes that were seen less than min_reads times)
    undetermined_r1 = open(os.path.join(out_dir, 'undetermined.r1.fastq'), 'w')
    undetermined_r2 = open(os.path.join(out_dir, 'undetermined.r2.fastq'), 'w')
    undetermined_i1 = open(os.path.join(out_dir, 'undetermined.i1.fastq'), 'w')
    undetermined_i2 = open(os.path.join(out_dir, 'undetermined.i2.fastq'), 'w')
    for sample_id in all_r1s.keys():
        for record in all_r1s[sample_id]:
            undetermined_r1.write(''.join(record))
        for record in all_r2s[sample_id]:
            undetermined_r2.write(''.join(record))
        for record in all_i1s[sample_id]:
            undetermined_i1.write(''.join(record))
        for record in all_i2s[sample_id]:
            undetermined_i2.write(''.join(record))

    # Close files
    for sample_id in outfiles_r1:
        outfiles_r1[sample_id].close()
        outfiles_r2[sample_id].close()
        outfiles_i1[sample_id].close()
        outfiles_i2[sample_id].close()
    undetermined_r1.close()
    undetermined_r2.close()
    undetermined_i1.close()
    undetermined_i2.close()

    logger.info('Wrote FASTQs for the %d sample barcodes out of %d with at least %d reads.', len(outfiles_r1), total_count, min_reads)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--read1', required=True)
    parser.add_argument('--read2', required=True)
    parser.add_argument('--index1', required=True)
    parser.add_argument('--index2', required=True)
    parser.add_argument('--min_reads', type=int, default=10000)
    parser.add_argument('--sample_barcodes')
    parser.add_argument('--out_dir', default='.')
    args = vars(parser.parse_args())

    demultiplex(args['read1'], args['read2'], args['index1'], args['index2'], args['sample_barcodes'], args['out_dir'], min_reads=args['min_reads'])

if __name__ == '__main__':
    main()
