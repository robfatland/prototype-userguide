'use strict';

/*
 * edge_sign.js — CloudFront Lambda@Edge (origin-request) for the OOI user-guide demo.
 *
 * Why this exists: CloudFront Origin Access Control (OAC) signs origin requests with SigV4,
 * but it does NOT include the request *body* in the signature. A Lambda Function URL with
 * AWS_IAM auth requires the payload hash, so POST requests with a body fail with
 * InvalidSignatureException. This origin-request trigger runs BEFORE CloudFront signs, and
 * sets x-amz-content-sha256 to the SHA256 of the body so the signature covers the payload.
 *
 * Must be deployed in us-east-1 and published as a numbered version to attach to a
 * distribution. See antonbabenko gist f9eee9603a525d55c3ae1abba1a561f5.
 */

const crypto = require('crypto');

exports.handler = (event, context, callback) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    const method = request.method;

    if (method !== 'POST' && method !== 'PUT' && method !== 'PATCH') {
        return callback(null, request);
    }

    let body = '';
    if (request.body && request.body.data) {
        body = request.body.encoding === 'base64'
            ? Buffer.from(request.body.data, 'base64').toString('utf8')
            : request.body.data;
    }

    const hash = crypto.createHash('sha256').update(body, 'utf8').digest('hex');
    headers['x-amz-content-sha256'] = [{ key: 'x-amz-content-sha256', value: hash }];

    return callback(null, request);
};
